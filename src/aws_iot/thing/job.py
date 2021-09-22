from .connector import IoTThingConnector, QUALITY_OF_SERVICE_AT_LEAST_ONCE
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTThingJobsClient
from AWSIoTPythonSDK.core.jobs.thingJobManager import (
    jobExecutionTopicType,
    jobExecutionTopicReplyType,
    jobExecutionStatus,
)
from abc import abstractmethod, ABC
from pathlib import Path
from threading import Thread
import json


__all__ = ["ThingJobHandler"]


class ThingJobHandler(ABC):
    """
    Custom AWS thing taking care of the underlying functions used in AWS IoT jobs
    """

    def __init__(
        self,
        thing_name: str = None,
        aws_region: str = None,
        endpoint: str = None,
        cert_path: (str, Path) = None,
        execute_open_jobs_on_init: bool = True,
        aws_thing_connector: IoTThingConnector = None,
    ):
        """
        Parameters
        ----------
        thing_name : str
            the name of the AWS thing
            needs to be identical to the name of an AWS thing as configured in the management console
        aws_region : str
            region of AWS thing management
        endpoint : str
            MQTT enpoint of the desired AWS account
        cert_path : str, Path
            directory of the certificates
        execute_open_jobs_on_init : bool, optional
            if open jobs for the thing should get executed on init or left pending
        aws_thing_connector : IoTThingConnector
            mqtt connection handler to AWS

        """

        if aws_thing_connector:
            self.__thing_connector = aws_thing_connector
        else:
            self.__thing_connector = IoTThingConnector(thing_name, aws_region, endpoint, cert_path)
            self.__thing_connector.connect()

        self.__jobs_done = True
        self.__jobs_started = int()
        self.__jobs_succeeded = int()
        self.__jobs_rejected = int()

        self.__create_aws_mqtt_jobs_client()
        if execute_open_jobs_on_init:
            self.__attempt_start_next_job()

    @property
    def thing(self):
        return self.__thing_connector

    def __create_aws_mqtt_jobs_client(self):
        self.__jobs_client = AWSIoTMQTTThingJobsClient(
            str(),
            thingName=self.thing.thing_name,
            QoS=QUALITY_OF_SERVICE_AT_LEAST_ONCE,
            awsIoTMQTTClient=self.thing.mqtt
        )

        self.__jobs_client.createJobSubscription(
            self.__new_job_received,
            jobExecutionTopicType.JOB_NOTIFY_NEXT_TOPIC
        )
        self.__jobs_client.createJobSubscription(
            self.__start_next_job_successfully_in_progress,
            jobExecutionTopicType.JOB_START_NEXT_TOPIC,
            jobExecutionTopicReplyType.JOB_ACCEPTED_REPLY_TYPE,
        )
        self.__jobs_client.createJobSubscription(
            self.__start_next_rejected,
            jobExecutionTopicType.JOB_START_NEXT_TOPIC,
            jobExecutionTopicReplyType.JOB_REJECTED_REPLY_TYPE,
        )

        self.__jobs_client.createJobSubscription(
            self.__update_job_successful,
            jobExecutionTopicType.JOB_UPDATE_TOPIC,
            jobExecutionTopicReplyType.JOB_ACCEPTED_REPLY_TYPE,
            "+",
        )
        self.__jobs_client.createJobSubscription(
            self.__update_job_rejected,
            jobExecutionTopicType.JOB_UPDATE_TOPIC,
            jobExecutionTopicReplyType.JOB_REJECTED_REPLY_TYPE,
            "+",
        )

    def __start_next_job_successfully_in_progress(self, client, userdata, message):
        payload = json.loads(message.payload.decode("utf-8"))
        if "execution" in payload:
            job_document = payload["execution"]["jobDocument"]
            job_id = payload["execution"]["jobId"]
            job_version_number = payload["execution"]["versionNumber"]
            job_execution_number = payload["execution"]["executionNumber"]

            try:
                self.execute(
                    job_document,
                    job_id,
                    job_version_number,
                    job_execution_number,
                )
                Thread(
                    target=self.__jobs_client.sendJobsUpdate,
                    kwargs={
                        "jobId": job_id,
                        "status": jobExecutionStatus.JOB_EXECUTION_SUCCEEDED,
                        "expectedVersion": job_version_number,
                        "executionNumber": job_execution_number,
                    },
                ).start()
            except Exception as e:
                Thread(
                    target=self.__jobs_client.sendJobsUpdate,
                    kwargs={
                        "jobId": job_id,
                        "status": jobExecutionStatus.JOB_EXECUTION_FAILED,
                        "expectedVersion": job_version_number,
                        "executionNumber": job_execution_number,
                    },
                ).start()

        else:
            self.__jobs_done = True

    def __new_job_received(self, client, userdata, message):
        payload = json.loads(message.payload.decode("utf-8"))
        if "execution" in payload:
            self.__jobs_done = False
            self.__attempt_start_next_job()
        else:
            self.__jobs_done = True

    def __start_next_rejected(self, client, userdata, message):
        self.__jobs_rejected += 1

    def __update_job_successful(self, client, userdata, message):
        self.__jobs_succeeded += 1

    def __update_job_rejected(self, client, userdata, message):
        self.__jobs_rejected += 1

    def __attempt_start_next_job(self):
        Thread(
            target=self.__jobs_client.sendJobsStartNext
        ).start()

    @property
    def jobs_done(self):
        return self.__jobs_done

    @property
    def job_stats(self):
        return {
            "jobsStarted": self.__jobs_started,
            "jobsSucceeded": self.__jobs_succeeded,
            "jobsRejected": self.__jobs_rejected,
        }

    @abstractmethod
    def execute(self, job_document, job_id, version_number, execution_number):
        pass
