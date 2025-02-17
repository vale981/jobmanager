#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import time
import multiprocessing as mp
from multiprocessing.managers import BaseManager
import socket
import signal
import logging
import datetime
import threading
from numpy import random
import pytest
import shutil

import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import binfootprint
import progression as progress

TIMEOUT = 15

import warnings
warnings.filterwarnings('ignore', module='traitlets', append=False, category=DeprecationWarning)
warnings.filterwarnings('error', append=True)

import jobmanager

logging.getLogger('jobmanager').setLevel(logging.INFO)
# logging.getLogger('jobmanager').setLevel(logging.INFO)
# logging.getLogger('jobmanager.jobmanager.JobManager_Server').setLevel(logging.INFO)
logging.getLogger('jobmanager.signalDelay').setLevel(logging.INFO)
logging.getLogger('progression').setLevel(logging.ERROR)
logging.basicConfig(level = logging.INFO)



AUTHKEY = 'testing'
PORT = random.randint(30000, 40000)
SERVER = socket.gethostname()

def test_WarningError():
    try:
        warnings.warn("test warning, should be an error")
    except:
        pass
    else:
        assert False

def test_Signal_to_SIG_IGN():
    from jobmanager.jobmanager import Signal_to_SIG_IGN
    global PORT
    PORT += 1
    def f():
        Signal_to_SIG_IGN()
        print("before sleep")
        while True:
            time.sleep(1)
        print("after sleep")

        
    p = mp.Process(target=f)
    p.start()
    time.sleep(0.2)
    assert p.is_alive()
    print("[+] is alive")

    print("    send SIGINT")
    os.kill(p.pid, signal.SIGINT)
    time.sleep(0.2)
    assert p.is_alive()
    print("[+] is alive")
    
    print("    send SIGTERM")
    os.kill(p.pid, signal.SIGTERM)
    time.sleep(0.2)
    assert p.is_alive()
    print("[+] is alive")
    
    print("    send SIGKILL")
    os.kill(p.pid, signal.SIGKILL)
    time.sleep(0.2)
    assert not p.is_alive()
    print("[+] terminated")
    
def test_Signal_to_sys_exit():
    from jobmanager.jobmanager import Signal_to_sys_exit
    global PORT
    PORT += 1
    def f():
        Signal_to_sys_exit()
        while True:
            try:
                time.sleep(10)
            except SystemExit:
                print("[+] caught SystemExit, but for further testing keep running")
            else:
                return
        
    p = mp.Process(target=f)
    p.start()
    time.sleep(0.2)
    assert p.is_alive()
    print("[+] is alive")

    print("    send SIGINT")
    os.kill(p.pid, signal.SIGINT)
    time.sleep(0.2)
    assert p.is_alive()
    print("[+] is alive")
    
    print("    send SIGTERM")
    os.kill(p.pid, signal.SIGTERM)
    time.sleep(0.2)
    assert p.is_alive()
    print("[+] is alive")
    
    print("    send SIGKILL")
    os.kill(p.pid, signal.SIGKILL)
    time.sleep(0.2)
    assert not p.is_alive()
    print("[+] terminated")
    
def test_Signal_to_terminate_process_list():
    from jobmanager.jobmanager import Signal_to_sys_exit
    from jobmanager.jobmanager import Signal_to_terminate_process_list
    global PORT
    PORT += 1
    def child_proc():
        Signal_to_sys_exit()
        try:
            time.sleep(10)
        except:
            err, val, trb = sys.exc_info()
            print("PID {}: caught Exception {}".format(os.getpid(), err))
            
    def mother_proc():
        try:
            n = 3
            p = []
            for i in range(n):
                p.append(mp.Process(target=child_proc))
                p[-1].start()
    
            Signal_to_terminate_process_list(process_list=p, identifier_list=["proc_{}".format(i+1) for i in range(n)])
            print("spawned {} processes".format(n))        
            for i in range(n):
                p[i].join()
            print("all joined, mother ends gracefully")
            sys.exit()
        except SystemExit:
            return
        except Exception as e:
            sys.exit(-1)
            
    p_mother = mp.Process(target=mother_proc)
    p_mother.start()
    time.sleep(0.2)
    assert p_mother.is_alive()
    print("send SIGINT")
    os.kill(p_mother.pid, signal.SIGINT)
    time.sleep(0.2)
    assert not p_mother.is_alive()
    assert p_mother.exitcode == 0
    

 
def start_server(n, read_old_state=False, client_sleep=0.1, hide_progress=False, job_q_on_disk=False):
    print("START SERVER")
    args = range(1,n)
    with jobmanager.JobManager_Server(authkey       = AUTHKEY,
                                      port          = PORT,
                                      msg_interval  = 1,
                                      const_arg     = client_sleep,
                                      fname_dump    = 'jobmanager.dump',
                                      hide_progress = hide_progress,
                                      job_q_on_disk = job_q_on_disk) as jm_server:
        if not read_old_state:
            jm_server.args_from_list(args)
        else:
            jm_server.read_old_state()
        jm_server.start()        
    
def start_client(hide_progress=True):
    print("START CLIENT")
    jm_client = jobmanager.JobManager_Client(server  = SERVER,
                                             authkey = AUTHKEY,
                                             port    = PORT,
                                             nproc   = 3,
                                             reconnect_tries = 0,
                                             hide_progress = hide_progress)
    jm_client.start()
    
def test_start_server_with_no_args():
    global PORT
    PORT += 1
    n = 10
    args = range(1,n)
    
    with jobmanager.JobManager_Server(authkey      = AUTHKEY,
                                      port         = PORT,
                                      msg_interval = 1,
                                      fname_dump   = 'jobmanager.dump') as jm_server:
        jm_server.start()    
    
def test_start_server():
    global PORT
    PORT += 1
    n = 10
    args = range(1,n)
    
    def send_SIGINT(pid):
        time.sleep(0.5)
        sys.stderr.write("send SIGINT\n")
        os.kill(pid, signal.SIGINT)    
    thr = threading.Thread(target=send_SIGINT, args=(os.getpid(),))
    thr.daemon = True    
    
    with jobmanager.JobManager_Server(authkey      = AUTHKEY,
                                      port         = PORT,
                                      msg_interval = 1,
                                      fname_dump   = 'jobmanager.dump') as jm_server:
        jm_server.args_from_list(args)       
        thr.start()
        jm_server.start()
    
def test_jobmanager_static_client_call():
    global PORT
    PORT += 1   
    jm_client = jobmanager.JobManager_Client(server  = SERVER,
                                             authkey = AUTHKEY,
                                             port    = PORT,
                                             nproc   = 3,
                                             reconnect_tries = 0)
    jm_client.func(arg=1, const_arg=1)


@pytest.mark.skipif(sys.version_info.major == 2,
                    reason="causes unknown trouble")
def test_client():
    global PORT
    PORT += 1    
    p_server = None
    n = 5

    try:
        # start a server
        p_server = mp.Process(target=start_server, args=(n,False,0.5))
        p_server.start()
        time.sleep(0.5)
        
        jmc = jobmanager.JobManager_Client(server  = SERVER,
                                           authkey = AUTHKEY,
                                           port    = PORT,
                                           nproc   = 3,
                                           reconnect_tries = 0)
        jmc.start()
        
        p_server.join(5)
        assert not p_server.is_alive(), "server did not end on time"
        
    except:
        if p_server is not None:
            p_server.terminate()
        raise


        

def test_jobmanager_basic():
    """
    start server, start client, process trivial jobs, quit
    
    check if all arguments are found in final_result of dump
    """
    global PORT
   
    
    for jqd in [False, True]:
        PORT += 1
        n = 5
        p_server = None
        p_client = None

        try:
            # start a server
            p_server = mp.Process(target=start_server, args=(n,False), kwargs={'job_q_on_disk': jqd})
            p_server.start()
            time.sleep(0.5)
            # server needs to be running
            assert p_server.is_alive()
        
            # start client
            p_client = mp.Process(target=start_client)
            p_client.start()
            
            p_client.join(10)
            # client should have processed all
            if sys.version_info.major == 2:
                p_client.terminate()
                p_client.join(3)
    
            assert not p_client.is_alive(), "the client did not terminate on time!"
            # client must not throw an exception
            assert p_client.exitcode == 0, "the client raised an exception"
            p_server.join(5)
            # server should have come down
            assert not p_server.is_alive(), "the server did not terminate on time!"
            assert p_server.exitcode == 0, "the server raised an exception"
            print("[+] client and server terminated")
              
            fname = 'jobmanager.dump'
            with open(fname, 'rb') as f:
                data = jobmanager.JobManager_Server.static_load(f)
            
            
            final_res_args_set = {a[0] for a in data['final_result']}
            set_ref = set(range(1,n))
            intersect = set_ref - final_res_args_set
              
            assert len(intersect) == 0, "final result does not contain all arguments!"
            print("[+] all arguments found in final_results")
        except:
            if p_server is not None:
                p_server.terminate()
            if p_client is not None:
                p_client.terminate()
            raise
    
def test_jobmanager_server_signals():
    """
        start a server (no client), shutdown, check dump 
    """
    global PORT
    timeout = 5
    n = 15
    sigs = [('SIGTERM', signal.SIGTERM), ('SIGINT', signal.SIGINT)]
    
    for signame, sig in sigs:
        PORT += 1
        p_server = None   
        try:
            print("## TEST {} ##".format(signame))
            p_server = mp.Process(target=start_server, args=(n,))
            p_server.start()
            time.sleep(0.5)
            assert p_server.is_alive()
            print("    send {}".format(signame))
            os.kill(p_server.pid, sig)
            print("[+] still alive (assume shut down takes some time)")
            p_server.join(timeout)
            assert not p_server.is_alive(), "timeout for server shutdown reached"
            assert p_server.exitcode == 0, "the server raised an exception"
            print("[+] now terminated (timeout of {}s not reached)".format(timeout))
            
            fname = 'jobmanager.dump'
            with open(fname, 'rb') as f:
                data = jobmanager.JobManager_Server.static_load(f)    

            ac = data['job_q']
            assert ac.qsize() == n-1
            assert ac.marked_items() == 0

            print("[+] args_set from dump contains all arguments")
        except:
            if p_server is not None:
                p_server.terminate()
            raise
    
def test_shutdown_server_while_client_running():
    """
    start server with 100 elements in queue
    
    start client
    
    stop server -> client should catch exception, but can't do anything, 
        writing to fail won't work, because server went down
        except do emergency dump
    
    check if the final_result and the args dump end up to include
    all arguments given 
    """
    global PORT
   
    n = 100

    sigs = [('SIGTERM', signal.SIGTERM), ('SIGINT', signal.SIGINT)]

    for signame, sig in sigs:
        PORT += 1
    
        p_server = None
        p_client = None
        
        try:
            p_server = mp.Process(target=start_server, args=(n,False,0.1))
            p_server.start()       
            time.sleep(0.5)
            assert p_server.is_alive()
            
            p_client = mp.Process(target=start_client)
            p_client.start()
            time.sleep(2)
            assert p_client.is_alive()
            
            print("    send {} to server".format(signame))
            os.kill(p_server.pid, sig)
            
            p_server.join(TIMEOUT)
            assert not p_server.is_alive(), "server did not shut down on time"
            assert p_server.exitcode == 0, "the server raised an exception"
            p_client.join(TIMEOUT)
            assert not p_client.is_alive(), "client did not shut down on time"
            assert p_client.exitcode == 0, "the client raised an exception"


            print("[+] server and client joined {}".format(datetime.datetime.now().isoformat()))
            
            fname = 'jobmanager.dump'
            with open(fname, 'rb') as f:
                data = jobmanager.JobManager_Server.static_load(f)    
        
            ac = data['job_q']
            args_set = {binfootprint.dump(ac.data['_'+str(id_)]) for id_ in ac._not_gotten_ids}
            final_result = data['final_result']
        
            final_res_args = {binfootprint.dump(a[0]) for a in final_result}
                
            args_ref = range(1,n)
            set_ref = set()
            for a in args_ref:
                set_ref.add(binfootprint.dump(a))    
            
            set_recover = set(args_set) | set(final_res_args)
            
            intersec_set = set_ref-set_recover
        
            if len(intersec_set) == 0:
                print("[+] no arguments lost!")
        
            assert len(intersec_set) == 0, "NOT all arguments found in dump!"
        except:
            if p_server is not None:
                p_server.terminate()
            if p_client is not None:
                p_client.terminate()
            raise

def test_shutdown_client():
    shutdown_client(signal.SIGTERM)
    shutdown_client(signal.SIGINT)

def shutdown_client(sig):
    """
    start server with 100 elements in queue
    
    start client
    
    stop client -> client should catch exception, interrupts the running worker function,
        reinsert arguments, client terminates
        
    start client again, continues to work on the queue
    
    if server does not terminate on time, something must be wrong with args_set
    check if the final_result contain all arguments given 
    """
    global PORT
    PORT += 1
    n = 30
    
    print("## terminate client with {} ##".format(progress.signal_dict[sig]))

    p_server = None
    p_client = None
    
    try:
        p_server = mp.Process(target=start_server, args=(n, False, 0.4, True))
        p_server.start()

        time.sleep(0.5)

        p_client = mp.Process(target=start_client)
        p_client.start()

        time.sleep(3)

        print("    send {}".format(progress.signal_dict[sig]))
        os.kill(p_client.pid, sig)
        assert p_client.is_alive()
        print("[+] still alive (assume shut down takes some time)")
        p_client.join(5)
        assert not p_client.is_alive(), "timeout for client shutdown reached"
        print("[+] now terminated (timeout of 5s not reached)")

        time.sleep(0.5)

        p_client = mp.Process(target=start_client)
        p_client.start()

        p_client.join(TIMEOUT)
        p_server.join(TIMEOUT)

        assert not p_client.is_alive()
        assert not p_server.is_alive()

        print("[+] client and server terminated")

        fname = 'jobmanager.dump'
        with open(fname, 'rb') as f:
            data = jobmanager.JobManager_Server.static_load(f)

        ac = data['job_q']
        assert ac.qsize() == 0
        print("[+] args_set is empty -> all args processed & none failed")

        final_res_args_set = {a[0] for a in data['final_result']}

        set_ref = set(range(1,n))

        intersect = set_ref - final_res_args_set

        assert len(intersect) == 0, "final result does not contain all arguments!"
        print("[+] all arguments found in final_results")
    except:
        if p_server is not None:
            p_server.terminate()
        if p_client is not None:
            p_client.terminate()
        raise

def test_jobmanager_read_old_stat():
    """
    start server, start client, start process trivial jobs,
    interrupt in between, restore state from dump, finish.
    
    check if all arguments are found in final_result of dump
    """
    global PORT
    PORT += 1
    n = 50
    p_server = mp.Process(target=start_server, args=(n,))
    p_server.start()
    
    time.sleep(1)
     
    p_client = mp.Process(target=start_client)
    p_client.start()
    
    time.sleep(1.5)

    # terminate server ... to start again using reload_from_dump
    p_server.terminate()
     
    p_client.join(10)
    p_server.join(10)


    assert not p_server.is_alive(), "the server did not terminate on time!"

    try:
        assert not p_client.is_alive(), "the client did not terminate on time!"
    except AssertionError:
        p_client.terminate()
        raise

    assert p_client.exitcode == 0
    assert p_server.exitcode == 0
    print("[+] client and server terminated")
    
    time.sleep(1)
    PORT += 1
    # start server using old dump
    p_server = mp.Process(target=start_server, args=(n,True))
    p_server.start()
    
    time.sleep(2)
     
    p_client = mp.Process(target=start_client)
    print("trigger start client")
    p_client.start()

    p_client.join(30)
    p_server.join(30)
 
    assert not p_client.is_alive(), "the client did not terminate on time!"
    assert not p_server.is_alive(), "the server did not terminate on time!"
    assert p_client.exitcode == 0
    assert p_server.exitcode == 0
    print("[+] client and server terminated")    
     
    fname = 'jobmanager.dump'
    with open(fname, 'rb') as f:
        data = jobmanager.JobManager_Server.static_load(f)
    
    final_res_args_set = {a[0] for a in data['final_result']}
         
    set_ref = set(range(1,n))
     
    intersect = set_ref - final_res_args_set
    print(intersect)
     
    assert len(intersect) == 0, "final result does not contain all arguments!"
    print("[+] all arguments found in final_results")    


def test_client_status():
    global PORT
    PORT += 1
    n = 10
    p_server = None
    
    try:
        p_server = mp.Process(target=start_server, args=(n,False,None, True))
        p_server.start()
        
        time.sleep(1)
        
        class Client_With_Status(jobmanager.JobManager_Client):
            def func(self, args, const_args, c, m):
                m.value = 30
                for i in range(m.value):
                    c.value = i+1
                    time.sleep(0.05)
     
                return os.getpid()
    
        client = Client_With_Status(server  = SERVER, 
                                    authkey = AUTHKEY,
                                    port    = PORT, 
                                    nproc   = 4)
        client.start()
        p_server.join(5)
        assert not p_server.is_alive()
    except:
        if p_server is not None:
            p_server.terminate()
        raise
    
def test_jobmanager_local():
    global PORT
    PORT += 1
    args = range(1,201)
    client_sleep = 0.1
    num_client = 4
    t0 = time.time()
    with jobmanager.JobManager_Local(client_class = jobmanager.JobManager_Client,
                                     authkey      = AUTHKEY,
                                     port         = PORT,
                                     const_arg    = client_sleep,
                                     nproc        = num_client) as jm_server:
        jm_server.args_from_list(args)
        jm_server.start()
    
    assert jm_server.all_successfully_processed()
    t1 = time.time()
    print("local JM, nproc {}".format(num_client))
    print("used time : {:.3}s".format(t1-t0))
    print("ideal time: {}s".format(len(args)*client_sleep/num_client))


        
def test_start_server_on_used_port():
    global PORT
    PORT += 1
    def start_server():
        const_arg = None
        arg = [10,20,30]
        with jobmanager.JobManager_Server(authkey = AUTHKEY,
                                          port    = PORT, 
                                          const_arg=const_arg,
                                          fname_dump=None) as server:
            server.args_from_list(arg)
            server.start()
            
    def start_server2():
        const_arg = None
        arg = [10,20,30]
        with jobmanager.JobManager_Server(authkey=AUTHKEY,
                                          port = PORT, 
                                          const_arg=const_arg,
                                          fname_dump=None) as server:
            server.args_from_list(arg)
            server.start()
            
    p1 = mp.Process(target=start_server)
    p1.start()
    
    time.sleep(1)
       
    try:
        start_server2()
    except (RuntimeError, OSError) as e:
        print("caught Exception '{}' {}".format(type(e).__name__, e))
    except:
        raise
    finally:
        time.sleep(1)
        p1.terminate()
        time.sleep(1)
        p1.join()    
            
def test_shared_const_arg():
    global PORT
    PORT += 1
    def start_server():
        const_arg = {1:1, 2:2, 3:3}
        arg = [10,20,30]
        with jobmanager.JobManager_Server(authkey=AUTHKEY,
                                          port = PORT, 
                                          const_arg=const_arg,
                                          fname_dump=None) as server:
            server.args_from_list(arg)
            server.start()
            
        print("const_arg at server side", const_arg)
            
    def start_client():
        class myClient(jobmanager.JobManager_Client):
            @staticmethod
            def func(arg, const_arg):
                const_arg[os.getpid()] = os.getpid() 
                print(os.getpid(), arg, const_arg)
                return None
            
        client = myClient(server=SERVER,
                          authkey=AUTHKEY,
                          port = PORT,
                          nproc=1)
        
        client.start()
            
    PORT += 1
    p1 = mp.Process(target=start_server)
    p2 = mp.Process(target=start_client)
    
    p1.start()
    
    time.sleep(1)
    
    p2.start()
    
    p2.join()
    
    time.sleep(1)
    p1.join()
    
def test_digest_rejected():
    global PORT
    PORT += 1
    n = 10
    p_server = mp.Process(target=start_server, args=(n,False))
    p_server.start()
    
    time.sleep(1)
    
    class Client_With_Status(jobmanager.JobManager_Client):
        def func(self, args, const_args, c, m):
            m.value = 100
            for i in range(m.value):
                c.value = i+1
                time.sleep(0.05)

            return os.getpid()

    client = Client_With_Status(server = SERVER, 
                                authkey = AUTHKEY+' not the same',
                                port    = PORT, 
                                nproc   = 4)
    try:
        client.start()
    except ConnectionError as e:
        print("Not an error: caught '{}' with message '{}'".format(e.__class__.__name__, e))
        p_server.terminate()
        
    p_server.join()
            
def test_hum_size():  
    # bypassing the __all__ clause in jobmanagers __init__
    from jobmanager.jobmanager import humanize_size
      
    assert humanize_size(1) == '1.00kB'
    assert humanize_size(110) == '0.11MB'
    assert humanize_size(1000) == '0.98MB'
    assert humanize_size(1024) == '1.00MB'
    assert humanize_size(1024**2) == '1.00GB'
    assert humanize_size(1024**3) == '1.00TB'
    assert humanize_size(1024**4) == '1024.00TB'

def test_ArgsContainer():
    from jobmanager.jobmanager import ArgsContainer
    from shutil import rmtree
    import shelve

    fname = "test.shelve"

    try:
        os.remove(fname)
    except FileNotFoundError:
        pass

    try:
        os.remove(fname+'.db')
    except FileNotFoundError:
        pass

    # simple test on shelve, close is needed to write data to disk
    s = shelve.open(fname)
    s['a'] = 1
    s.close()
    s2 = shelve.open(fname)
    assert s2['a'] == 1

    try:
        os.remove(fname)
    except FileNotFoundError:
        pass

    try:
        os.remove(fname+'.db')
    except FileNotFoundError:
        pass




    path = 'argscont'
    # remove old test data
    try:
        rmtree(path)
    except FileNotFoundError:
        pass

    ac = ArgsContainer(path)
    try:                            # error as ac already exists on disk
        ac = ArgsContainer(path)
    except RuntimeError:
        pass
    else:
        assert False
    ac.clear()                      # remove ac from disk

    #for p in [None, path]:
    for p in [path]:

        ac = ArgsContainer(p)
        for arg in 'abcde':
            ac.put(arg)

        assert ac.qsize() == 5
        item1 = ac.get()
        item2 = ac.get()
        
        assert ac.qsize() == 3
        assert ac.marked_items() == 0
        assert ac.unmarked_items() == 5
        
        # reinserting a non marked item is allowed
        ac.put(item1)
        assert ac.qsize() == 4
        assert ac.marked_items() == 0
        assert ac.unmarked_items() == 5
        
        # marking an item that has not been gotten yet failes
        try:
            ac.mark(item1)
        except ValueError:
            pass
        else:
            assert False
        assert ac.qsize() == 4
        assert ac.marked_items() == 0
        assert ac.unmarked_items() == 5    
            
                
        ac.mark(item2)
        assert ac.qsize() == 4
        assert ac.marked_items() == 1
        assert ac.unmarked_items() == 4

        # already marked items can not be reinserted        
        try:
            ac.put(item2)
        except:
            pass
        else:
            assert False
        
        assert ac.qsize() == 4
        assert ac.marked_items() == 1
        assert ac.unmarked_items() == 4

        # remarking raises a RuntimeWarning
        try:
            ac.mark(item2)
        except RuntimeWarning:
            pass
        else:
            assert False
            
        item3 = ac.get()
        assert ac.qsize() == 3
        assert ac.marked_items() == 1
        assert ac.unmarked_items() == 4

        import pickle
        ac_dump = pickle.dumps(ac)
        ac.close_shelve() # the shelve need to be closed, so that the data gets flushed to disk

        
        # note here, when loading, the _not_gottem_id are all ids
        # except the marked its
        ac2 = pickle.loads(ac_dump)

        assert ac2.qsize() == 4
        from jobmanager.jobmanager import bf, hashlib

        item3_hash = hashlib.sha256(bf.dump(item3)).hexdigest()
        assert item3_hash in ac2.data
        assert ac2.marked_items() == 1
        assert ac2.unmarked_items() == 4
        
        ac2.get()
        ac2.get()
        ac2.get()
        item = ac2.get()
        assert ac2.qsize() == 0
        assert ac2.marked_items() == 1
        assert ac2.unmarked_items() == 4
        
        ac2.mark(item)      
        assert ac2.qsize() == 0
        assert ac2.marked_items() == 2
        assert ac2.unmarked_items() == 3

        import queue
        try:
            ac2.get()
        except queue.Empty:
            pass
        else:
            assert False

        ac2.clear()

def put_from_subprocess(port):
    class MM_remote(BaseManager):
        pass
    try:
        MM_remote.register('get_job_q')
        m = MM_remote(('localhost', port), b'test_argscomnt')
        m.connect()
        ac = m.get_job_q()
        for item in range(1, 200):
            ac.put(item)
            time.sleep(0.01)
            
    except ValueError:
        pass


def test_ArgsContainer_BaseManager():
    from jobmanager.jobmanager import ArgsContainer
    global PORT
       
    path = 'argscont'
    from shutil import rmtree
    try:
        rmtree(path)
    except FileNotFoundError:
        pass
    
    for p in [path, None]:
        PORT += 1
        ac_inst = ArgsContainer(p)
        #ac_inst.close_shelve()
        class MM(BaseManager):
            pass
        MM.register('get_job_q', callable=lambda: ac_inst, exposed = ['put', 'get'])
       
        def start_manager_thread():
            m = MM(('', PORT), b'test_argscomnt')

            m.get_server().serve_forever()
        server_thr = threading.Thread(target=start_manager_thread, daemon=True)

        
        class MM_remote(BaseManager):
            pass
        
        MM_remote.register('get_job_q')
        m = MM_remote(('localhost', PORT), b'test_argscomnt')
        
        
        server_thr.start()
        m.connect()
        
        
        
        pr = mp.Process(target = put_from_subprocess, args=(PORT,))
        pr.start()
        
        try:
            for arg in range(200, 0,-1):
                ac_inst.put(arg)
                time.sleep(0.01)
        except ValueError:
            pass
            
        pr.join()
        assert pr.exitcode == 0
        print(ac_inst.qsize())

        assert ac_inst.qsize() == 200

        ac_inst.clear()



def test_ArgsContainer_BaseManager_in_subprocess():
    from jobmanager.jobmanager import ArgsContainer
    from jobmanager.jobmanager import ContainerClosedError
    import queue
    global PORT

    path = 'argscont'
    from shutil import rmtree
    try:
        rmtree(path)
    except FileNotFoundError:
        pass

    for p in [path, None]:
        PORT += 1
        ac_inst = ArgsContainer(p)
        ac_inst.put('a')
        assert ac_inst.qsize() == 1
        assert ac_inst.gotten_items() == 0
        assert ac_inst.marked_items() == 0


        class MM(BaseManager):
            pass

        q = ac_inst.get_queue()
        MM.register('get_job_q', callable=lambda: q, exposed=['put', 'get'])
        m = MM(('', PORT), b'test_argscomnt')
        m.start()

        class MM_remote(BaseManager):
            pass

        MM_remote.register('get_job_q')
        mr = MM_remote(('localhost', PORT), b'test_argscomnt')
        mr.connect()

        acr = mr.get_job_q()
        acr.put('b')
        acr.put('c')
        time.sleep(0.1)

        assert ac_inst.qsize() == 3
        assert ac_inst.gotten_items() == 0
        assert ac_inst.marked_items() == 0


        it = ac_inst.get()
        assert ac_inst.qsize() == 2
        assert ac_inst.gotten_items() == 1
        assert ac_inst.marked_items() == 0

        ac_inst.mark(it)
        assert ac_inst.qsize() == 2
        assert ac_inst.gotten_items() == 1
        assert ac_inst.marked_items() == 1

        it = acr.get()
        assert ac_inst.qsize() == 1
        assert ac_inst.gotten_items() == 2
        assert ac_inst.marked_items() == 1

        ac_inst.mark(it)
        assert ac_inst.qsize() == 1
        assert ac_inst.gotten_items() == 2
        assert ac_inst.marked_items() == 2


        acr.get()
        assert ac_inst.qsize() == 0
        try:
            acr.get()
        except queue.Empty:
            print("caught queue.Empty")
        else:
            assert False

        acr.put('e')
        time.sleep(0.1)

        assert ac_inst.qsize() == 1

        ac_inst.close()
        try:
            acr.put('f')
        except ContainerClosedError:
            print("caught ContainerClosedError")
        else:
            assert False

        try:
            acr.get()
        except ContainerClosedError:
            print("caught ContainerClosedError")
        else:
            assert False

        ac_inst.clear()
            
def test_havy_load_on_ArgsContainer():
    from jobmanager.jobmanager import ArgsContainer
    from jobmanager.jobmanager import ContainerClosedError
    import queue
    global PORT

    path = 'argscont2'
    from shutil import rmtree
    try:
        rmtree(path)
    except FileNotFoundError:
        pass
    
    for p in [path, None]:
        PORT += 1
        ac_inst = ArgsContainer(p)
        for i in range(2000):
            ac_inst.put(i)

        q = ac_inst.get_queue()
           
        time.sleep(1)
        
        class MM(BaseManager):
            pass    
        MM.register('get_job_q', callable=lambda: q, exposed=['put', 'get'])
        m = MM(('', PORT), b'test_argscomnt')
        m.start()
        
        def cl():
            m = MM(('', PORT), b'test_argscomnt')
            m.connect()
            qr = m.get_job_q()
            for i in range(50):
                item = qr.get()
                qr.put(item)
                
        plist = []
        for i in range(40):
            pr = mp.Process(target=cl)
            plist.append(pr)
        
        for pr in plist:
            pr.start()
            
        for pr in plist:
            pr.join()
            assert pr.exitcode == 0
            
        m.shutdown()
        time.sleep(1)
        
        print(ac_inst.qsize())
        ac_inst.clear()
            

def test_ClosableQueue():
    from jobmanager.jobmanager import ClosableQueue
    from jobmanager.jobmanager import ContainerClosedError
    import queue
    
    q = ClosableQueue()
        
    def get_on_empty_q(q):
        try:
            q.get(timeout=0.1)
        except queue.Empty:
            pass
        else:
            assert False
    get_on_empty_q(q)
    
    p = mp.Process(target=get_on_empty_q, args=(q,))
    p.start()
    p.join()
    assert p.exitcode == 0
    
    q = ClosableQueue()
    
    # doing things local
    d = {'key': 'value'}
    
    q.put(1)
    q.put('a')
    q.put(d)
    assert q.get() == 1
    assert q.get() == 'a'
    assert q.get() == d 
    
    # put data in subprocess to queue
    def put_in_sp(q):
        q.put(1)
        q.put('a')
        q.put({'key': 'value'})
    p = mp.Process(target=put_in_sp, args=(q,))
    p.start()
    p.join()
    assert p.exitcode == 0
    assert q.get() == 1
    assert q.get() == 'a'
    assert q.get() == d
    
    # get data in subprocess from queue
    def get_in_sp(q):
        assert q.get() == 1
        assert q.get() == 'a'
        assert q.get() == d
        
    q.put(1)
    q.put('a')
    q.put(d)
    p = mp.Process(target=get_in_sp, args=(q,))
    p.start()
    p.join()
    assert p.exitcode == 0
    
    
    q = ClosableQueue()
    q.put(1)
    q.put('a')
    q.close()
    def put_on_closed_q(q):
        try:
            q.put(None)
        except ContainerClosedError:
            pass
        else:
            assert False            
    put_on_closed_q(q)
        
    p = mp.Process(target=put_on_closed_q, args=(q,))
    p.start()
    p.join()
    assert p.exitcode == 0
    
        
    
def test_ClosableQueue_with_manager():
    
    from jobmanager.jobmanager import ClosableQueue
    from jobmanager.jobmanager import ContainerClosedError
    from multiprocessing.managers import BaseManager
    import pickle
    
    class MM(BaseManager):
        pass
    
    q = ClosableQueue()
    q_client = q.client()

    MM.register('q', callable = lambda: q_client, exposed=['get', 'put', 'qsize'])    
    m = MM(address=('', 12347), authkey=b'b')
    
    
    
    m.start()
    
    m_remote = MM(address=('', 12347), authkey=b'b')
    m_remote.connect()
    q_remote = m_remote.q()
    
    m_remote2 = MM(address=('', 12347), authkey=b'b')
    m_remote2.connect()
    q_remote2= m_remote.q()
    
    m_remote3 = MM(address=('', 12347), authkey=b'b')
    m_remote3.connect()
    q_remote3 = m_remote.q()
    
    q.put(0)
    q_remote.put(1)
    q_remote.put('a')
    q_remote2.put(2)
    q_remote2.put('b')
    q_remote3.put(3)
    q_remote3.put('c')
    
    time.sleep(0.5)
    
    print(q.get(timeout=1))
    print(q.get(timeout=1))
    print(q.get(timeout=1))
    print(q.get(timeout=1))
    print(q.get(timeout=1))
    print(q.get(timeout=1))
    
    
    
if __name__ == "__main__":
    logging.getLogger('jobmanager').setLevel(logging.INFO)
    if len(sys.argv) > 1:
        pass
    else:    
        func = [
            # test_ArgsContainer,
            # test_ArgsContainer_BaseManager,
            # test_ArgsContainer_BaseManager_in_subprocess,
            # test_havy_load_on_ArgsContainer,
            # test_ClosableQueue,
            # test_ClosableQueue_with_manager,
            # test_hum_size,
            # test_Signal_to_SIG_IGN,
            # test_Signal_to_sys_exit,
            # test_Signal_to_terminate_process_list,
            # test_jobmanager_static_client_call,
            # test_start_server_with_no_args,
            # test_start_server,
            # test_client,
            # test_jobmanager_basic,
            # test_jobmanager_server_signals,
            # test_shutdown_server_while_client_running,
            # test_shutdown_client,
            # test_jobmanager_read_old_stat,
            # test_client_status,
            test_jobmanager_local,
            # test_start_server_on_used_port,
            # test_shared_const_arg,
            # test_digest_rejected,
            # test_hum_size,

        lambda : print("END")
        ]
        for f in func:
            print()
            print('#'*80)
            print('##  {}'.format(f.__name__))
            print()
            f()
            #time.sleep(1)

    for f in os.listdir('./'):
        if f.endswith('.dump'):
            os.remove('./{}'.format(f))
        elif f.endswith('_jobqdb'):
            shutil.rmtree('./{}'.format(f))