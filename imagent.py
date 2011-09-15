#!/bin/python
"""
This program is designed to replicate virtual machines image files on virtualization hypervisors.
It downloads the VMDK files from a webserver. It gets the available image lists from OpenStack Glance server.
It can run both in stand-alone server mode or in cron job mode (you would need to configure crontab file). 
See help of this progam.

Copyright (C) 2011  

Authors (alphabetically):
	Arsalaan Ahmed Shaikh (CERN, Switzerland)
	Omer Khalid (CERN, Switzerland) 
        
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
                        
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
                                        
You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

####################################################################################################
## Import statements

import sys
import traceback
import os
import shutil
import time
import logging
import optparse
####################################################################################################
## Global variables

copies = 0
imageList = []
updateListRemote = []
updateListLocal = []
idList = []
glance_server = ""
data_store = ""
download_server = ""
logger=None
verbose=None
runmode=None
sleepTime=10
firstRun=True
####################################################################################################
def getImageList():
	global imageList
	global updateListRemote
	global idList
	global firstRun
	
	localImageList = []
	localUpdateListRemote = []
	localIdList = []
	
	os.system("wget "+glance_server+"/images/detail -O "+data_store+"IM/imagelist.txt")
	infile = open(data_store+"IM/imagelist.txt","r")
	line = infile.readline()
	listData = line.split(',')
	infile.close()
	for item in listData:
		if item.startswith(' "name"'):
			localImageList.append(item.split(': ')[1].split('"')[1])
		if item.startswith(' "updated_at"'):
			localUpdateListRemote.append(item.split(': ')[1].split('"')[1])
		if item.startswith(' "id"'):
			localIdList.append(item.split(': ')[1])
	#BUG FIX: prevents duplicated entries to be added to the list
	if firstRun != True:
		imageList.pop()
		updateListRemote.pop()
		idList.pop()
	imageList = localImageList
	updateListRemote = localUpdateListRemote
	idList = localIdList
	firstRun=False
	
	#DEBUG CODE
	logger.debug("getImageUpdate() -> globalImageList[]: " + str(imageList))
	logger.debug("getImageUpdate() -> localImageList[]: " + str(localImageList))
	logger.debug("getImageUpdate() -> globalUpdateListRemote[]: " + str(updateListRemote))
	logger.debug("getImageUpdate() -> localUpdateListRemote[]: " + str(localUpdateListRemote))
	logger.debug("getImageUpdate() -> globalIdList[]: " + str(idList))
	logger.debug("getImageUpdate() -> localIdList[]: " + str(localIdList))
#####################################################################################################
def readUpdateFile():
	try:
		updatefile = open(data_store+"IM/update.txt","r")
		uData = updatefile.readline().replace('\n','').split(';')
		updatefile.close()
		for item in uData:
			updateListLocal.append(item)
	except IOError, err:
		logging.error("Update.txt file is missing. Error: %s" % err)
		sys.exit(0)
#####################################################################################################
def writeUpdateFile():

	line = ""
	index = 0
	os.remove(data_store+"IM/update.txt")
	for imID in idList:
		if(line != ""):
			line+=";"
		line+= imID+","+updateListRemote[index]+","+imageList[index]
		index+=1
	updatefile = open(data_store+"IM/update.txt","w")
	updatefile.write(line)
	updatefile.close()
#####################################################################################################
def checkIsUpdate(index):
	if os.path.isfile(data_store+"IM/Template/"+imageList[index]+"/"+imageList[index]+".vmdk"):
		logger.debug("Yes, FILE is there: "+imageList[index])
		for item in updateListLocal:
			data = item.split(',')
			if data[0] == idList[index]:
				if data[1] != updateListRemote[index]:
					logger.info("'UPDATING TEMPLATE "+ data[0])
					os.remove(data_store+"IM/Template/"+imageList[index]+"/"+imageList[index]+".vmdk")
					download_img_cmd= "wget "+download_server+"/images/"+idList[index]+"/"+imageList[index]+".vmdk"+" -O "+data_store+"IM/Template/"+imageList[index]+"/"+imageList[index]+".vmdk"
					logger.info("Executing: " + download_img_cmd)
					os.system(download_img_cmd)
	else:
		logger.info('FILE is not there: '+imageList[index])
		download_img_cmd = "wget "+download_server+"/images/"+idList[index]+"/"+imageList[index]+".vmdk"+" -O "+data_store+"IM/Template/"+imageList[index]+"/"+imageList[index]+".vmdk"
		logger.info("Executing: " + download_img_cmd)
		os.system(download_img_cmd)
#####################################################################################################
def checkTemplate():
	index = 0
	for item in imageList:
		if os.path.isdir(data_store+"IM/Template/"+item):
			logger.debug("Yes, DIR is there: "+item)
			checkIsUpdate(index)
		else:
			logger.info("DIR is not there: "+item)
			os.makedirs(data_store+"IM/Template/"+item)
			download_img_cmd="wget "+download_server+"/images/"+idList[index]+"/"+item+".vmdk"+" -O "+data_store+"IM/Template/"+item+"/"+item+".vmdk"
			logger.info("Executing: " + download_img_cmd)
			os.system(download_img_cmd)
		index+=1
#####################################################################################################
def checkVMReady():
	for index in range(0,copies):
		logger.info("Check VM Ready")
		for item in imageList:
			if not os.path.isdir(data_store+item+str(index+1)+"/"):
				os.makedirs(data_store+item+str(index+1)+"temp/")
				shutil.copy(data_store+"IM/Template/"+item+"/"+item+".vmdk", data_store+item+str(index+1)+"temp/"+item+".vmdk")
				os.rename(data_store+item+str(index+1)+"temp/",data_store+item+str(index+1)+"/")
#####################################################################################################
def readConf():
	conffile = open("/etc/IM.conf", "r")
	data = conffile.read().split("\n")
	global copies
	global glance_server
	global data_store
	global download_server
	logger.debug("Config file data: " + str(data))
	for item in data:
		if item.startswith("GLANCE"):
			glance_server += item.split("=")[1]
		if item.startswith("DATA"):			
			data_store += item.split("=")[1]
		if item.startswith("NO"):
			copies+= int(item.split("=")[1])
		if item.startswith("DOWNLOAD"):
			download_server+= item.split("=")[1]
	conffile.close()

#####################################################################################################
def deleteVM():
	for item in updateListLocal:
		flag="false"
		data = item.split(',')
		for imID in idList:
			if data[0] == imID:
				flag="true"
				
		if flag == "false":
			shutil.rmtree(data_store+"IM/Template/"+data[2]+"/")
			for index in range(0,copies):
				shutil.rmtree(data_store+data[2]+str(index+1)+"/")
				index+=1

#####################################################################################################
def initLogger():
	# create logger
	global logger
	global verbose
	
	logger = logging.getLogger("image_manager")
	
	# create console handler and set level to debug
	ch = logging.StreamHandler()
	
	if verbose==0:
		logger.setLevel(logging.ERROR)
		ch.setLevel(logging.ERROR)
	elif verbose==1:
		logger.setLevel(logging.WARN)
		ch.setLevel(logging.WARN)
	elif verbose==2:
		logger.setLevel(logging.INFO)
		ch.setLevel(logging.INFO)
	elif verbose==3:
		logger.setLevel(logging.DEBUG)
		ch.setLevel(logging.DEBUG)
	
	# create formatter
	formatter = logging.Formatter("[%(asctime)s] [%(levelname)s]: %(message)s ","%Y-%m-%d %H:%M:%S")
	
	# add formatter to ch
	ch.setFormatter(formatter)
	
	# add ch to logger
	logger.addHandler(ch)
	
	# "application" code
	#logger.debug("debug message")
	#logger.info("info message")
	#logger.warn("warn message")
	#logger.error("error message")
	#logger.critical("critical message")


#####################################################################################################
def serverMode():
	global sleepTime
	logger.info("Starting image agent service")
	while True:
		getImageList()
		readUpdateFile()
		checkTemplate()
		writeUpdateFile()
		checkVMReady()
		deleteVM()
		logger.info("IDLE- Going to sleep")
		time.sleep(sleepTime)

#####################################################################################################
def cronMode():
	logger.info("Starting image agent service")
	getImageList()
	readUpdateFile()
	checkTemplate()
	writeUpdateFile()
	checkVMReady()
	deleteVM()
	logger.info("Finished updating.")
	
#####################################################################################################
def xtraDebugInfo():
	logger.debug("imageList: " + str(imageList[1]))
	logger.debug("idList: " + str(idList[1]))
	logger.debug("updateListLocal: " + str(updateListLocal))

#####################################################################################################
def parseCmdLineOptions():
	global runmode
	global verbose
	
	parser = optparse.OptionParser("usage: %prog [options]", version="%prog 1.0")
	
	#set default values to prevent confusion
	parser.set_defaults(runmode="cron",verbose=1)
	
	parser.add_option("-c", "--cron", dest="runmode",
			action="store_const", const="cron",
			help="run in cron mode. Default option is cron")
	parser.add_option("-s", "--server", dest="runmode",
			action="store_const", const="server",
			help="run in server mode. Default option is cron")
        
        parser.add_option("-q", "--quiet", action="store_const", const=0, dest="verbose",
			help="run the program quietly. Only error messages will be shown.")
        
        parser.add_option("-v", "--verbose", action="count", dest="verbose",
			help="run the program with different level of verbosity: -v, -vv")
	
	(options, args) = parser.parse_args()
	
	if options.verbose:
		verbose = options.verbose
	if options.runmode:
		runmode = options.runmode
		
	optList = []
	optList.append(runmode)
	optList.append(verbose)
	
	# logging is not initialzied yet; using print statement
	
	print "ARGV	:", sys.argv[1:]
	print "Option values passed: "+ str(options)
	print "Options values set: "+ str(optList)
        
#####################################################################################################
def main():
	try:
		# handle unintended inputs to prevent the program from crashing
		try:
			parseCmdLineOptions()
		except:
			print "Using default configuration to run. Error: " % traceback.print_exc()
			pass

		initLogger()
		readConf()

		if runmode=="cron":
			cronMode()
		elif runmode=="server":
			serverMode()
		else:
			cronMode()
	except:
		logger.error("Unexepected Error: %s" % traceback.print_exc())
	finally:
		logger.info("Good bye, image agent service is terminating.")


#####################################################################################################
if __name__ == "__main__":
	sys.exit(main())
