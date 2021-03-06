# import threading
import time
from typing import Set
from cryptography.fernet import Fernet


# This lock is used to get access to print onto the standard output
from Locks.MasterPrintLock import master
from Communication.protocol import YACS_Protocol
from Scheduler.JobRequests import JobRequestHandler
from MasterUtils.WorkerStateTracker import StateTracker


# PRINT_LOCK = threading.Lock()


class RoundRobinScheduler:
    """ The ```RoundRobinScheduler``` class implements the **Round-Robin
    Scheduling** algorithm. In this algorithm  The machines are ordered based
    on worker_id of the Worker running on the machine. The Master picks a
    machine in round-robin fashion. If the machine does not have a free slot,
    the Master moves on to the next worker_id in the ordering. This process
    continues until a free slot is found.
    """
    @staticmethod
    def jobDispatcher(requestHandler: JobRequestHandler,
                      workerStateTracker: StateTracker,
                      WORKER_COUNT: int):
        """```jobDispatcher``` implements the **Round-Robin
        Scheduling** algorithm.

        **param** ```requestHandler```: This object will track the tasks of
        incomplete jobs, and provide them for allocation, respecting the
        *map-reduce* dependency

        **type** ```requestHandler```: JobRequestHandler

        **param** ```workerStateTracker```: This object will track and update
        how loaded the workers are, i.e. how many free slots fo they have

        **type** ```workerStateTracker```: StateTracker

        **param** ```WORKER_COUNT```: Contains the count for the number of
        workers

        **type** ```WORKER_COUNT```: int
        """
        workerIDsVisited: Set = set()
        _temp: int = 0  # Initially we begin at the first worker

        while True:
            jobID_family_task = None

            # Get a pending task, if any
            requestHandler.LOCK.acquire()
            if not requestHandler.isEmpty():
                jobID_family_task = requestHandler.getWaitingTask()
            requestHandler.LOCK.release()

            # If there is a Task that needs to be executed
            if jobID_family_task is not None:
                # Initially we have not visited any worker
                workerIDsVisited.clear()

                # Initially we have not found a worker with a free slot
                workerFound: bool = False

                while workerFound is False:  # Until a free worker is not found

                    workerStateTracker.LOCK.acquire()
                    workerIDsVisited.add(workerStateTracker.workerIDs[_temp])

                    # If the worker has a free slot
                    if workerStateTracker \
                            .isWorkerFree(workerStateTracker.workerIDs[_temp]):
                        # Create the JSON protocol message
                        protocolMsg = (YACS_Protocol
                                       .createMessageToWorker
                                       (
                                        job_ID=jobID_family_task[0],
                                        task_family=jobID_family_task[1],
                                        task_ID=(jobID_family_task[2]
                                                 ["task_id"]),
                                        duration=(jobID_family_task[2]
                                                  ["duration"]),
                                        worker_ID=workerStateTracker
                                        .workerIDs[_temp]
                                       ))
                        # Once a worker with a free slot is found then
                        # 1. We dispatch the job to the worker
                        # 2. Update its state
                        enc_obj = Fernet(workerStateTracker
                                         .workerState[workerStateTracker
                                                      .workerIDs[_temp]]
                                         ["pri_key"])
                        workerStateTracker.getWorkerSocket(workerStateTracker.
                                                           workerIDs[_temp])\
                            .sendall(enc_obj.encrypt(protocolMsg.encode()))

                        master.PRINT_LOCK.acquire()
                        print(f"Sending task to worker: {protocolMsg}")
                        master.PRINT_LOCK.release()
                        workerStateTracker.allocateSlot(workerStateTracker
                                                        .workerIDs[_temp])
                        master.PRINT_LOCK.acquire()
                        workerStateTracker.showWorkerStates()
                        master.PRINT_LOCK.release()

                        requestHandler.LOCK.acquire()
                        _state = requestHandler.jobRequests
                        requestHandler.LOCK.release()
                        master.PRINT_LOCK.acquire()
                        print(f"requestHandler.jobRequests={_state}")
                        master.PRINT_LOCK.release()

                        # We have found a worker and hence set this to True
                        workerFound = True

                    workerStateTracker.LOCK.release()

                    _temp += 1
                    _temp %= WORKER_COUNT

                    # In the case where none of the workers have a free slot
                    if (workerFound is False) and \
                        (list(workerIDsVisited) ==
                            workerStateTracker.workerIDs):
                        # Sleep for a second to allow for the
                        # workerStateTracker to be updated by the
                        # thread: workerUpdates
                        time.sleep(1)

                        # Clear the worker IDs visited set as we are
                        # restarting our search for a free slot on one of the
                        # workers
                        workerIDsVisited.clear()

                # After sending a task to the worker, sleep for 0.01 seconds
                # before sending the next task. This done so that the worker
                # buffer only has at most 1 task in its socket's buffer
                # time.sleep(0.01)
