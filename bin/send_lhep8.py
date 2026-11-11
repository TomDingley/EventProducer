#!/usr/bin/env python3
import os, sys
import subprocess
import time
import yaml
import glob
import re
import shlex
from pathlib import Path
from select import select
import EventProducer.common.utils as ut
import EventProducer.common.makeyaml as my

class send_lhep8():

#__________________________________________________________
    def __init__(self,njobs, events, process, islsf, iscondor, islocal, queue, priority, ncpus, para, version, decay, pycard, detector, custom_edm4hep_config, dry_run=False, prepare_only=False):

        self.njobs    = njobs
        self.events   = events
        self.process  = process
        self.islsf    = islsf
        self.iscondor = iscondor
        self.islocal  = islocal
        self.queue    = queue
        self.priority = priority
        self.ncpus    = ncpus
        self.para     = para
        self.version  = version
        self.decay    = decay
        self.pycard   = pycard
        self.detector = detector
        self.user     = os.environ['USER']
        self.custom_edm4hep_config = custom_edm4hep_config
        self.dry_run = dry_run
        self.prepare_only = prepare_only

#__________________________________________________________
    def send(self, force):

        Dir = os.getcwd()
    
        gplist=self.para.gridpacklist
        outdir='%s%s/%s/'%(self.para.delphes_dir,self.version,self.detector)
        try:
            gplist[self.process]
        except KeyError as e:
            print ('process %s does not exist as gridpack'%self.process)
            sys.exit(3)

        # retrieve delphes card paths for FCC-hh case
        if "FCChh" in self.para.module_name and not "trackCov" in self.detector:
            delphescards_mmr='' #not sure this is really necessary, could clean up the code to not need it
            delphescards_emr=''
            delphescards_mr=''

            #ensure backwards compatibility for old productions (directory structure changes from v06)
            prod_version_num = int(re.search(r'v([\d]+)', self.version).group(1))

            if prod_version_num >= 6:
                # Base card
                delphescards_base = os.path.join(self.para.delphescards_dir, self.para.delphescard_base)
                
                # Separate momentum resolution parametrization for muons
                delphescards_mmr = os.path.join(self.para.delphescards_dir, self.para.delphescard_mmr)
            
                # Separate momentum resolution parametrization for tracks
                delphescards_mr = os.path.join(self.para.delphescards_dir, self.para.delphescard_mr)

                # Separate momentum resolution parametrization for electrons - exists only from production v05 onwards!
                delphescards_emr = os.path.join(self.para.delphescards_dir, self.para.delphescard_emr)

            else:
                delphescards_base = '%s%s/%s'%(self.para.delphescards_dir,self.version,self.para.delphescard_base)
                delphescards_mmr = '%s%s/%s'%(self.para.delphescards_dir,self.version,self.para.delphescard_mmr)
                delphescards_mr = '%s%s/%s'%(self.para.delphescards_dir,self.version,self.para.delphescard_mr)

                if prod_version_num >= 5:
                    delphescards_emr = '%s%s/%s'%(self.para.delphescards_dir, self.version, self.para.delphescard_emr)


            # replace detector version tag
            delphescards_base = delphescards_base.replace('DETECTOR',self.detector)
            delphescards_mmr = delphescards_mmr.replace('DETECTOR',self.detector)
            delphescards_mr = delphescards_mr.replace('DETECTOR',self.detector)
            delphescards_emr = delphescards_emr.replace('DETECTOR',self.detector)

            #check if all requested cards exist:
            if not os.path.isfile(delphescards_base):
                raise Exception("ERROR in param_FCChh - the base Delphes card doesn't exist, at: "+delphescards_base)

            if not os.path.isfile(delphescards_mmr):
                raise Exception("ERROR in param_FCChh - the card for muon momentum resolution doesn't exist, at: "+delphescards_mmr)

            if not os.path.isfile(delphescards_mr):
                raise Exception("ERROR in param_FCChh - the card for track momentum resolution doesn't exist, at: "+delphescards_mr)

            if not os.path.isfile(delphescards_emr) and prod_version_num >= 5:
                raise Exception("ERROR in param_FCChh - the card for track momentum resolution doesn't exist, at: "+delphescards_emr)
        
        #Support for TrackCov card only added for > v07 onwards
        elif "FCChh" in self.para.module_name and "trackCov" in self.detector:
            delphescards_base = os.path.join(self.para.delphescards_dir, self.para.delphescard_base).replace('DETECTOR',self.detector)

            if not os.path.isfile(delphescards_base):
                raise Exception("ERROR in param_FCChh - the base Delphes card doesn't exist, at: "+delphescards_base)

        # retrieve delphes card paths for FCC-ee case
        # 2021/09/08 :
        else:
            delphescards_base = '%scard_%s.tcl'%(self.para.delphescards_dir,self.detector)
            delphescards_base=delphescards_base.replace('_VERSION_',self.version)
            fccee_pythiacards_dir = self.para.pythiacards_dir.replace('_VERSION_',self.version)
            print( 'fccee_pythiacards_dir =', fccee_pythiacards_dir)

            if ut.file_exist(delphescards_base)==False:
                print ('delphes card does not exist: ',delphescards_base)
                sys.exit(3)

        if 'FCCee' not in self.para.module_name:
             fccconfig = '%s%s'%(self.para.fccconfig_dir,self.para.fccconfig)
             if ut.file_exist(fccconfig)==False:
                 print ('fcc config file does not exist: ',fccconfig)
                 sys.exit(3)


        print ('======================================',self.process)
        
        '''
        pythiacard='%s%s.cmd'%(self.para.pythiacards_dir,self.process.replace('mg_pp','p8_pp').replace('mg_gg','p8_gg'))
        if self.decay!='':
            pythiacard='%s%s_%s.cmd'%(self.para.pythiacards_dir,self.process.replace('mg_pp','p8_pp').replace('mg_gg','p8_gg'),self.decay)
            
        if ut.file_exist(pythiacard)==False and not force:
            print 'pythia card does not exist: ',pythiacard
            timeout = 60
            print "do you want to use the default pythia card [y/n] (60sec to reply)"
            rlist, _, _ = select([sys.stdin], [], [], timeout)
            if rlist:
                s = sys.stdin.readline()
                if s=="y\n":
                    print 'use default card'
                    if 'FCCee' not in self.para.module_name: pythiacard='%sp8_pp_default.cmd'%(self.para.pythiacards_dir)
                    else: pythiacard='%sp8_ee_default.cmd'%(self.para.pythiacards_dir)
                else:
                    print 'exit'
                    sys.exit(3)
            else:
                print "timeout, use default card"
                pythiacard='%sp8_pp_default.cmd'%(self.para.pythiacards_dir)
        elif ut.file_exist(pythiacard)==False and force:
            print "force argument, use default card"
            pythiacard='%sp8_pp_default.cmd'%(self.para.pythiacards_dir)

        pr_noht=''
        if '_HT_' in self.process:
            ssplit=self.process.split('_')
            stest=''
            for s in xrange(0,len(ssplit)-3):
                stest+=ssplit[s]+'_'
            pr_noht= stest[0:len(stest)-1]

        #check that the specified decay exists
        if self.process in self.para.decaylist and self.decay != '' and '_HT_' not in self.process:
            if self.decay not in self.para.decaylist[self.process]:
                print 'decay ==%s== does not exist for process ==%s=='%(self.decay,self.process)
                sys.exit(3)

        #check that the specified decay exists
        if pr_noht in self.para.decaylist and self.decay != '' and '_HT_' in self.process:
            if self.decay not in self.para.decaylist[pr_noht]:
                print 'decay ==%s== does not exist for process ==%s=='%(self.decay,self.process)
                sys.exit(3)
        '''

        '''
        if self.pycard == 'p8_pp_default.cmd':
            print 'using default pythia card: p8_pp_default.cmd'
            pythiacard=self.para.pythiacards_dir+'/'+self.pycard

        #if 'FCCee' in self.process:
            #pythiacard = fccee_pythiacards_dir+'/'+self.pycard
            #print 'using pythia card: ',pythiacard
        elif 
        '''

        pythiacard=self.para.pythiacards_dir+'/'+self.pycard
        if 'FCCee' in self.para.module_name:
            pythiacard = fccee_pythiacards_dir+'/'+self.pycard
            print('Using Pythia card: ',pythiacard)

        if not os.path.isfile(pythiacard):
            print ('{} does not exist'.format(pythiacard))
            sys.exit(3)

        pr_decay = self.process       
        if self.process in self.para.decaylist and self.decay != '':
            pr_decay=self.process
            print ('====',pr_decay,'====')
            pr_decay=self.process+'_'+self.decay


        # first string before underscore is generator
        mcprg_str = pr_decay.split('_')[0]
        processp8 = pr_decay.replace(mcprg_str, mcprg_str+'p8')

        print (processp8)

        acctype='FCC'
        if 'HELHC' in self.para.module_name:  acctype='HELHC'
        elif 'FCCee' in self.para.module_name:  acctype='FCCee'

        # logdir=Dir+"/BatchOutputs/%s/%s/%s/%s/"%(acctype,self.version,self.detector,processp8)
        #TEMO OVERWRITE !!
        logdir=str(Path(getattr(self.para, 'batch_dir', Dir+'/BatchOutputs')) / acctype / self.version / self.detector / processp8)

        if self.dry_run:
            print(f'Dry run: up to {self.njobs} Delphes jobs, {self.events} events/job; output {outdir}{processp8}')
            print(f'LHE records: {self.para.yamldir}lhe/{self.process}; Pythia card: {pythiacard}')
            return

        if not ut.dir_exist(logdir):
            os.system("mkdir -p %s"%logdir)

        #yamldir = '%s/%s/%s'%(self.para.yamldir,self.version,processp8)
        #if not ut.dir_exist(yamldir):
            #os.system("mkdir -p %s"%yamldir)
        if not self.islocal:
            yamldir = '%s/%s/%s/%s'%(self.para.yamldir,self.version,self.detector,processp8)
            print( "yamldir = ",yamldir )
            if not ut.dir_exist(yamldir):
                os.system("mkdir -p %s"%yamldir)

        yamllhedir = '%s/lhe/%s'%(self.para.yamldir,self.process)
  
        All_files = sorted(glob.glob("%s/events_*.yaml"%yamllhedir))
        if len(All_files)==0:
            print ('there is no LHE files checked for process %s exit'%self.process)
            print(' yamllhedir =',yamllhedir)
            sys.exit(3)

        if len(All_files)<self.njobs:
            print ('only %i LHE file exists, will not run all the jobs requested'%len(All_files))

        nbjobsSub=0
        ntmp=0

        if self.islsf==False and self.iscondor==False and self.islocal==False:
            print ("Submit issue : LSF nor CONDOR flag defined !!!")
            sys.exit(3)

        condor_file_str=''
        
        for i in range(len(All_files)):

            if nbjobsSub == self.njobs: break
            
            tmpf=None
            with open(All_files[i], 'r') as stream:
                try:
                    #tmpf = yaml.load(stream, Loader=yaml.FullLoader)
                    tmpf = yaml.load(stream, Loader=yaml.FullLoader)
                    if ut.getsize(All_files[i])==0:continue
                    if tmpf['processing']['status']!='DONE': continue
                    
                except yaml.YAMLError as exc:
                    print(exc)

            jobid=str(tmpf['processing']['jobid'])
            pythiaseed = jobid
            print("jobid = ",jobid)
            # because of too long seeds used in the KKMC production of Oct 10, 2021:
            if len(jobid)>11:
                pythiaseed=jobid[11:]  

            if not self.islocal:
                myyaml = my.makeyaml(yamldir, jobid)
                if not myyaml: 
                    print ('job %s already exists'%jobid)
                    continue

                outfile='%s/%s/events_%s.root'%(outdir,processp8,jobid)
                if ut.file_exist(outfile):
                    print ('outfile already exist, continue  ',outfile)
                    continue

            if self.islocal:
                outfile='%s/events_%s.root'%(logdir,jobid)
                if ut.file_exist(outfile):
                    print ('file %s already locally exist, continue'%outfile)
                    continue

            frunname = 'job%s.sh'%(jobid)
            frunfull = '%s/%s'%(logdir,frunname)

            frun = None
            try:
                frun = open(frunfull, 'w')
            except IOError as e:
                print ("I/O error({0}): {1}".format(e.errno, e.strerror))
                time.sleep(10)
                frun = open(frunfull, 'w')

            subprocess.getstatusoutput('chmod 777 %s'%(frunfull))
            q = lambda value: shlex.quote(str(value))
            frun.write('#!/bin/bash\n')
            frun.write('unset LD_LIBRARY_PATH\nunset PYTHONHOME\nunset PYTHONPATH\n')
            frun.write('source %s || exit 1\n' % self.para.prodTag[self.version])
            frun.write('mkdir job%s_%s || exit 1\n' % (jobid, processp8))
            frun.write('cd job%s_%s || exit 1\n' % (jobid, processp8))
            frun.write('mkdir -p %s || exit 1\n' % q(Path(outfile).parent))
            frun.write('cp %s events.lhe.gz || exit 1\n' % q(tmpf['processing']['out']))
            frun.write('gunzip -c events.lhe.gz > events.lhe || exit 1\n')
            frun.write('cp %s card.tcl || exit 1\n' % q(delphescards_base))
            if 'FCChh' in self.para.module_name and 'trackCov' not in self.detector:
                for card in (delphescards_mmr, delphescards_mr, delphescards_emr):
                    if card:
                        frun.write('cp %s . || exit 1\n' % q(card))
            if self.custom_edm4hep_config:
                edm_config = Path(self.custom_edm4hep_config).resolve()
            elif 'FCChh' in self.para.module_name:
                edm_config = Path(self.para.fccconfig_dir) / self.para.fccconfig
            else:
                edm_config = Path('/eos/experiment/fcc/ee/generation/FCC-config') / self.version / 'FCCee/Delphes' / ('edm4hep_%s.tcl' % self.detector)
            if not edm_config.is_file():
                raise FileNotFoundError(edm_config)
            frun.write('cp %s edm4hep_output_config.tcl || exit 1\n' % q(edm_config))
            frun.write('cp %s card.cmd || exit 1\n' % q(pythiacard))
            frun.write('echo "Beams:LHEF = events.lhe" >> card.cmd\n')
            frun.write('echo "Random:seed = %s" >> card.cmd\n' % int(pythiaseed))
            event_count = min(self.events, int(tmpf['processing']['nevents']))
            frun.write('echo "Main:numberOfEvents = %i" >> card.cmd\n' % event_count)
            binary = getattr(self.para, 'delphes_binary', 'DelphesPythia8_EDM4HEP')
            frun.write('%s card.tcl edm4hep_output_config.tcl card.cmd events.root || exit 1\n' % q(binary))
            frun.write('cp events.root %s || exit 1\n' % q(outfile))
            frun.close()

            if self.islsf==True :
              cmdBatch="bsub -M 3000000 -R \"pool=40000\" -q %s -o %s -cwd %s %s" %(self.queue, logdir+'/job%s/'%(jobid), logdir+'/job%s/'%(jobid),frunfull)

              batchid=-1
              job,batchid=ut.SubmitToLsf(cmdBatch,10,"%i/%i"%(nbjobsSub,self.njobs))
              nbjobsSub+=job
            elif self.iscondor==True :
              condor_file_str+=frunfull+" "
              nbjobsSub+=1

            elif self.islocal==True:
                print ('will run locally')
                nbjobsSub+=1
                os.system('%s'%frunfull)


        if nbjobsSub == 0:
            print('No eligible LHE files to submit')
            return

        if self.iscondor==True :
            # clean string
            condor_file_str=condor_file_str.replace("//","/")
            #
            frunname_condor = 'job_desc_lhep8.cfg'
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
            frun_condor.write('executable     = $(filename)\n')
            frun_condor.write('Log            = %s/condor_job.%s.$(ClusterId).$(ProcId).log\n'%(logdir,str(jobid)))
            frun_condor.write('Output         = %s/condor_job.%s.$(ClusterId).$(ProcId).out\n'%(logdir,str(jobid)))
            frun_condor.write('Error          = %s/condor_job.%s.$(ClusterId).$(ProcId).error\n'%(logdir,str(jobid)))

            # FCC-hh legacy production v05 with special release can only run on centos7 container, 
            # and for v06 we set up from newer releases and dont want to port env
            if 'FCChh' in self.para.module_name:
                if "fcc_v05" in self.version:
                    frun_condor.write('MY.WantOS = "el7"\n')
                else:
                    frun_condor.write('requirements    = ( (OpSysAndVer =?= "AlmaLinux9") && (Machine =!= LastRemoteHost) && (TARGET.has_avx2 =?= True) )\n')
                
                frun_condor.write('environment    = "LS_SUBCWD=%s"\n'%logdir) 

            else:
                frun_condor.write('getenv         = True\n')
                frun_condor.write('environment    = "LS_SUBCWD=%s"\n'%logdir) # not sure
                frun_condor.write('requirements    = ( (OpSysAndVer =?= "AlmaLinux9") && (Machine =!= LastRemoteHost) && (TARGET.has_avx2 =?= True) )\n')

            frun_condor.write('on_exit_remove = (ExitBySignal == False) && (ExitCode == 0)\n')
            frun_condor.write('max_retries    = 3\n')
            frun_condor.write('+JobFlavour    = "%s"\n'%self.queue)
            frun_condor.write('+AccountingGroup = "%s"\n'%self.priority)
            frun_condor.write('RequestCpus = %s\n'%self.ncpus)
            frun_condor.write('request_memory = 8 GB\nrequest_disk = 10 GB\n')
            frun_condor.write('should_transfer_files = YES\nwhen_to_transfer_output = ON_EXIT\ntransfer_output_files = ""\n')

            frun_condor.write('queue filename matching files %s\n'%condor_file_str)
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


