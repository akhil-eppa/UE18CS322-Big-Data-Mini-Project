from threading import Lock


class JobRequestHandler:
    """This class stores the incoming job requests from the job request
     port. The incoming jobs are stored with a certain priority; at the
     moment First Come First Served technique is used. It also provides
     waiting tasks for the highest priority job request,
     in order of map tasks then reduce tasks.

    Once a job has been completely allocated to one or the worker. Its entry
     is removed from this object.
    """
    def __init__(self, workerUpdatesTracker):
        self.jobRequests = {}
        self.priorityOrder = []
        self.LOCK = Lock()
        self.workerUpdatesTracker = workerUpdatesTracker

    def addJobRequest(self, requestSpecs):
        """Adds the request specification to the objects
         jobRequests dictionary and adds the job ID to the
         priorityOrder list as per the priority order of the
         job.

        :param requestSpecs: Dictionary got after converting the incoming
         JSON request string into a dictionary
        :type requestSpecs: dict
        """
        _JOB_ID: int = requestSpecs["job_id"]
        self.jobRequests[_JOB_ID] = {
            "map": requestSpecs["map_tasks"],
            "reduce": requestSpecs["reduce_tasks"]
        }
        self.priorityOrder.append(requestSpecs["job_id"])

    def getWaitingTask(self, workerUpdatesTracker):
        """getWaitingTask returns a task to be allocated on one of the workers
        as well as task related meta-data

        Algorithm:
        ----------
        1. For every job in the jobRequests list:
            1.1 Check if the job has any pending map tasks
                1.1.1 Return any map task of the job and associated meta-data
            1.2 else
                1.2.1 Check if all the job's map tasks have completed
                    1.2.1.1 Return any reduce task of the job and associated
                            meta-data
                1.2.2 else
                    1.2.2.1 Continue and hence move to the next pending job
        2. Return None as there is no assignable task available to 

        :return: Task meta-data and the task dictionary
        :rtype: Tuple
        """
        # If there are no pending tasks and hence no pending jobs
        # then return None
        if len(self.priorityOrder) == 0:
            return None

        _JOB_ID = None
        _SELECTED_TASK = None
        _TASK_TYPE = None
        for jobID in self.jobRequests:
            # Check for a pending map task
            if self.jobRequests[jobID]["map"]:
                _SELECTED_TASK = self.jobRequests[jobID]["map"].pop(0)
                _TASK_TYPE = "map"
                _JOB_ID = jobID

            else:
                self.workerUpdatesTracker.LOCK.acquire()
                _temp = self.workerUpdatesTracker.isMapComplete(jobID)
                self.workerUpdatesTracker.LOCK.release()
                if _temp:
                    # Check for a pending reduce task
                    _SELECTED_TASK = self.jobRequests[jobID]["reduce"].pop(0)
                    _TASK_TYPE = "reduce"
                    _JOB_ID = jobID

        if (_SELECTED_TASK is None) and (_JOB_ID is None) and\
           (_TASK_TYPE is None):
            return None

        # Check if this task is the last task, if so then remove its
        # entry from this object's state
        if (not self.jobRequests[_JOB_ID]["map"]) and \
           (not self.jobRequests[_JOB_ID]["reduce"]):
            del self.jobRequests[_JOB_ID]
            self.priorityOrder.remove(_JOB_ID)

        return (_JOB_ID, _TASK_TYPE, _SELECTED_TASK)

    def isEmpty(self):
        return True if not self.priorityOrder else False
