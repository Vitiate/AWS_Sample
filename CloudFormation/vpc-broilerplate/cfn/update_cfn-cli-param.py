#!/usr/local/bin/python3
# May have to change the interpreter
import sys, getopt, shutil, os
from ruamel.yaml import YAML
# pip install ruamel.yaml first ***
# This script updates a parameter under a cfn-cli stage with a value. 

def backupFile(InFile):
	# Create a backup of the file we are modifying.
	dir = os.path.dirname(InFile)
	basename = os.path.basename(InFile)
	print("Backing up {} to {}/~{}".format(InFile, dir, basename))
	shutil.copy(InFile,"{}/~{}".format(dir, basename))

def updateParam(Parameter, Value, InFile):
	yaml = YAML()
	with open(InFile) as fp:
		data = yaml.load(fp)
		fp.close()
	for blueprint in data['Blueprints']:
		for item in data['Blueprints'][blueprint]['Tags']:
			if Parameter == item:
				print(f"Found {item} setting value to {Value}")
				data['Blueprints'][blueprint]['Tags'][item] = Value
				##data["Stages"][Stage][BP]["Parameters"][Parameter] = Value
	with open(InFile,"w") as ofp:
		yaml.dump(data, ofp)
		ofp.close()

def main(argv):
	CommandLine = 'apply_param.py -i <in file> -p <parameter> -v <value>'
	Parameter = ''
	Value = ''
	InFile = ''
	OutFile = ''
	try:
		opts, args = getopt.getopt(argv,"hi:p:v:",["in=", "parameter=", "value=", "out="])
	except getopt.GetoptError:
		print (CommandLine)
		sys.exit(2)
	if len(sys.argv) == 1:
		print (CommandLine)
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			print (CommandLine)
			sys.exit()
		elif opt in ("-p", "--parameter"):
			Parameter = arg
		elif opt in ("-v", "--value"):
			Value = arg
		elif opt in ("-i", "--in"):
			InFile = arg
	# Backup the file to ~InFile
	backupFile(InFile)
	# Load the file, and replace the value
	updateParam(Parameter, Value, InFile)	

if __name__ == "__main__":
   main(sys.argv[1:])
