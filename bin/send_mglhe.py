#python bin/run.py --FCC --LHE --send --version fcc_v02 -p dummy --typelhe mg --mg5card pp_hh.mg5 --model loop_sm_hh.tar -N 2 -n 10000 -q workday --condor

#!/usr/bin/env python
import os, sys
import subprocess
import time
import shlex
from pathlib import Path
import EventProducer.common.utils as ut
import EventProducer.common.makeyaml as my

class send_mglhe():

#__________________________________________________________
    def __init__(self, islsf, iscondor, mg5card, cutfile, model, para, procname, njobs, nev, queue, priority, ncpus, do_EL7, useV3=False, plugin="", reweight_card="", madspin_card="", dry_run=False, prepare_only=False):
        self.islsf     = islsf
        self.iscondor  = iscondor
        self.user      = os.environ['USER']
        self.mg5card   = mg5card
        self.cutfile   = cutfile
        self.model     = model
        self.para      = para
        self.procname  = procname
        self.njobs     = njobs
        self.nev       = nev
        self.queue     = queue
        self.priority  = priority
        self.ncpus     = ncpus
        self.do_EL7    = do_EL7
        self.useV3     = useV3
        self.plugin     = plugin
        self.reweight_card = reweight_card or ''
        self.madspin_card = madspin_card or ''
        self.dry_run = dry_run
        self.prepare_only = prepare_only

#__________________________________________________________
    def send(self):
        Dir = str(Path(__file__).resolve().parents[1])
        nbjobsSub=0

        # output dir
        outdir=self.para.lhe_dir

        acctype='FCC'
        if 'HELHC' in self.para.module_name:  acctype='HELHC'
        elif 'FCCee' in self.para.module_name:  acctype='FCCee'

        logdir=str(Path(getattr(self.para, 'batch_dir', Dir+'/BatchOutputs')) / acctype / 'lhe' / self.procname)
        for card in (self.mg5card, self.reweight_card, self.madspin_card):
            if card and not os.path.isfile(card):
                raise FileNotFoundError(card)
        if 'FCChh' in self.para.module_name and not os.path.isfile(self.para.mg5_dir+'/bin/mg5_aMC'):
            raise FileNotFoundError(self.para.mg5_dir+'/bin/mg5_aMC')
        if self.dry_run:
            print(f'Dry run: {self.njobs} MG5 jobs, {self.nev} events/job; output {outdir}{self.procname}')
            print(f'MG5 card: {self.mg5card}; reweight card: {self.reweight_card}; MadSpin card: {self.madspin_card}')
            return

        if not ut.dir_exist(logdir):
            os.system("mkdir -p %s"%logdir)

        yamldir = '%s/lhe/%s'%(self.para.yamldir,self.procname)
        if not ut.dir_exist(yamldir):
            os.system("mkdir -p %s"%yamldir)

        outdir  = os.path.abspath(outdir)
        mg5card = os.path.abspath(self.mg5card)
        cuts    = os.path.abspath(self.cutfile)
        model   = os.path.abspath(self.model) if self.model else ''
        reweight = os.path.abspath(self.reweight_card) if self.reweight_card else ''
        madspin = os.path.abspath(self.madspin_card) if self.madspin_card else ''
        if self.plugin:
            plugin   = os.path.abspath(self.plugin)
        else:
            plugin = ''

        jobsdir = logdir+'/'

        if not os.path.exists(jobsdir):
           os.makedirs(jobsdir)
           os.makedirs(jobsdir+'/std/')
           os.makedirs(jobsdir+'/cfg/')

        if self.islsf==False and self.iscondor==False:
            print ("Submit issue : LSF nor CONDOR flag defined !!!")
            sys.exit(3)

        condor_file_params_str=[]
        while nbjobsSub<self.njobs:
            uid = ut.getuid2()
            myyaml = my.makeyaml(yamldir, uid)
            if not myyaml: 
                print ('job %s already exists'%uid)
                continue

            if ut.file_exist('%s/%s/events_%s.lhe.gz'%(outdir,self.procname,uid)):
                print ('already exist, continue')
                continue
    
            print ('Submitting job '+str(nbjobsSub)+' out of '+str(self.njobs))
            seed = str(uid)
            
            basename =  self.procname+ '_'+seed

            cwd = os.getcwd()
            script = cwd + '/bin/submitMG.sh '
            if self.useV3 or 'FCChh' in self.para.module_name:
                script = cwd + '/bin/submitMG_v3.sh '
            script = Dir + '/bin/' + Path(script.strip()).name
            parameters = [mg5card, self.procname, outdir, seed, str(self.nev), cuts, model, plugin,
                          reweight, madspin,
                          getattr(self.para, 'mg5_dir', ''), getattr(self.para, 'lhapdf_config', ''),
                          getattr(self.para, 'generator_setup', '')]

            if self.islsf==True :
              cmdBatch = 'bsub -o '+jobsdir+'/std/'+basename +'.out -e '+jobsdir+'/std/'+basename +'.err -q '+self.queue
              cmdBatch +=' -J '+basename +' '+shlex.join([script, *parameters])

              print (cmdBatch)

              batchid=-1
              job,batchid=ut.SubmitToLsf(cmdBatch,10,1)
              nbjobsSub+=job
            elif self.iscondor==True :
              # Condor's quoted argument syntax preserves optional empty arguments.
              condor_arguments = ' '.join("'" + value.replace("'", "''") + "'" for value in parameters)
              condor_file_params_str.append('"' + condor_arguments.replace('"', '""') + '"')
              nbjobsSub+=1

        if self.iscondor==True :
            # parameter file
            fparamname_condor = 'job_params_mglhe.txt'
            fparamfull_condor = '%s/%s'%(logdir,fparamname_condor)
            fparam_condor = None
            try:
                fparam_condor = open(fparamfull_condor, 'w')
            except IOError as e:
                print ("I/O error({0}): {1}".format(e.errno, e.strerror))
                time.sleep(10)
                fparam_condor = open(fparamfull_condor, 'w')
            for line in condor_file_params_str:
                fparam_condor.write('%s\n'%line)
            fparam_condor.close()
            # condor config
            frunname_condor = 'job_desc_mglhe.cfg'
            frunfull_condor = '%s/%s'%(logdir,frunname_condor)
            frun_condor = None
            try:
                frun_condor = open(frunfull_condor, 'w')
            except IOError as e:
                print ("I/O error({0}): {1}".format(e.errno, e.strerror))
                time.sleep(10)
                frun_condor = open(frunfull_condor, 'w')
            subprocess.getstatusoutput('chmod 777 %s'%frunfull_condor)
            #
            frun_condor.write('executable     = %s\n'%script)
            frun_condor.write('Log            = %s/condor_job.%s.$(ClusterId).$(ProcId).log\n'%(logdir,str(uid)))
            frun_condor.write('Output         = %s/condor_job.%s.$(ClusterId).$(ProcId).out\n'%(logdir,str(uid)))
            frun_condor.write('Error          = %s/condor_job.%s.$(ClusterId).$(ProcId).error\n'%(logdir,str(uid)))

            if self.do_EL7:
                print("Info: requested to run in centos7 container.")
                frun_condor.write('MY.WantOS = "el7"\n')
                frun_condor.write('environment    = "LS_SUBCWD=%s"\n'%logdir) 
            else:
                frun_condor.write('getenv         = %s\n' % ('False' if 'FCChh' in self.para.module_name else 'True'))
                frun_condor.write('environment    = "LS_SUBCWD=%s"\n'%logdir) # not sure
                frun_condor.write('requirements   = (OpSysAndVer =?= "AlmaLinux9") && (TARGET.has_avx2 =?= True)\n')

            frun_condor.write('on_exit_remove = (ExitBySignal == False) && (ExitCode == 0)\n')
            frun_condor.write('max_retries    = 3\n')
            frun_condor.write('+JobFlavour    = "%s"\n'%self.queue)
            frun_condor.write('+AccountingGroup = "%s"\n'%self.priority)
            frun_condor.write('RequestCpus = %s\n'%self.ncpus)
            frun_condor.write('request_memory = 8 GB\nrequest_disk = 10 GB\n')
            frun_condor.write('should_transfer_files = YES\nwhen_to_transfer_output = ON_EXIT\ntransfer_output_files = ""\n')
            frun_condor.write('queue arguments from %s\n'%fparamfull_condor)
            frun_condor.close()
            #
            cmdBatch="condor_submit %s"%frunfull_condor
            print (cmdBatch)
            if self.prepare_only:
                print('Prepared jobs only; submit with:', cmdBatch)
            else:
                job=ut.SubmitToCondor(cmdBatch,10,"%i/%i"%(nbjobsSub,self.njobs))
                if not job:
                    raise RuntimeError('Condor submission failed')

        print('%s %i job(s)' % ('Prepared' if self.prepare_only else 'Submitted', nbjobsSub))

