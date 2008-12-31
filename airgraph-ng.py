#!/usr/bin/python
#Welcome to airgraph written by TheX1le
#Special Thanks to Rel1k and Zero_Chaos two people whom with out i would not be who I am!
#I would also like to thank muts and Remote Exploit Community for all their help and support!

########################################
#
# Airgraph-ng.py --- Generate Graphs from airodump CSV Files
#
# Copyright (C) 2005 Ben Smith <thex1le@gmail.com>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation; version 2.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
#########################################
# Import Psyco if available to speed up execution
try:
	import psyco
	psyco.full()
#	pass
except ImportError:
	print "Psyco optimizer not installed, You may want to download and install it!"


import getopt, subprocess, sys, pdb, optparse
sys.path.append("./lib/")
import lib_Airgraphviz   #note this should be further down
dot_libs = lib_Airgraphviz

#pdb.set_trace() #debug point
####################################
#      Global Vars                 # 
####################################
PROG = "airgraph-ng"
block = '\n####################################\n'

####################################
# Module to open aircrack dump     #
####################################

def airDumpOpen(file):
	try:
		raw_macs = open(file, "r")
	except Exception:
		print "Error Opening file ",file,". Please check and try again"
		sys.exit(1)
	Rmacs = raw_macs.readlines() #reads each line one at a time and store them a list
	cleanup = []
	for line in Rmacs: #iterates through the lines and strips of the new line and line returns ie \r\n
		cleanup.append(line.rstrip())
	raw_macs.close()
	return cleanup
####################################
# Modules to Parse targets into a  #
# Logical format for keeping track #
# of targets "bssid:info"          #
####################################
def airDumpParse(ardump):
	try: #some very basic error handeling to make sure they are loading up the correct file
		del ardump[0] #remove the first line of text with the headings
		stationStart = ardump.index('Station MAC, First time seen, Last time seen, Power, # packets, BSSID, Probed ESSIDs') 
	except Exception:
		print "You Seem to have provided an improper input file please make sure you are loading an airodump txt file and not a pcap"
		sys.exit(1)
	del ardump[stationStart] #this removes the client Station Mac, ect heading.....
	Clients = ardump[stationStart:] #splits off the clients into their own list
	del ardump[stationStart:]#removed all of the client info leaving only the info on available target AP's in ardump maby i should create a new list for APs?
	def dictCreate(device):
		dict = {}
		for entry in device: #the following loop through the Clients List creates a nexsted list of each client in its own list grouped by a parent list of client info
			entry = entry.replace(' ','') #remove spaces
			string_list = entry.split(',') #splits the string line and turns it into a list object
			if string_list[0] != '':
				dict[string_list[0]] = string_list[:] #if the line isnt a blank line then it is stored in dictionlary with the MAC/BSSID as the key
		return dict			
	ApDict = dictCreate(ardump)
	ClientsDict = dictCreate(Clients)
	retVar = [ClientsDict,ApDict]
	return retVar

##################################
# User land information          #
##################################

def about():
	print block , "#     Welcome to",PROG,"      #" , block
def showBanner():
	print "Usage",PROG,"-i [airodumpfile.txt] -o [outputfile.png] -g [CAPR OR CPG]\n\t-i\tInput File\n\t-o\tOutput File\n\t-g\tChoose the Graph Type Current types are [CAPR (Client to AP Relationship) & CPG (Common probe graph)]\n\t-a\tPrint the about\n\t-h\tPrint this help"

###################################
#          Graphviz work          #
###################################

def dot_create(info,graph_type):
	#please dont try to use this feature yet its not finish and will error	
	def ZKS_main(info): # Zero_Chaos Kitchen Sink Mode..... Every Thing but the Kitchen Sink!
		#info comes in as list Clients Dictionary at postion 0 and AP Dictionary at postion1
		#print "Feature is not ready yet"
		#sys.exit(1)
		#pdb.set_trace() #debug point
		return_var = CAPR_main(info)
		#dot_file = return_var[0]
		APNC = return_var[2]
		CNAP = return_var[3]
		CAPR = return_var[0]
		del CAPR[:1] #remove the graphviz heading...
		dot_file = ['digraph G {\n\tsize ="96,96";\n\toverlap=scale;\n'] #start the graphviz config file
		dot_file.extend(dot_libs.subgraph(CAPR,'Clients to AP Relationships','CAPR','n'))

		if len(APNC) != 0: # there should be a better way to check for null lists
			dot_file.extend(dot_libs.subgraph(APNC,'Acess Points with no Clients','AP'))
		if len(CNAP) != 0:
			dot_file.extend(dot_libs.subgraph(CNAP,'Clients that are Not Assoicated','Clients'))
		footer = ['test','test']
		return_lst = [dot_file,footer]
		return return_lst


	def CPG_main(info): #CPG stands for Common Probe Graph
		#info comes in a list Clients Dictionary at postion 0 and AP Dictionary at postion 1
		Clients = info[0]
		AP = info[1]
		Clients_list = [] #keep trakc of our clients
		Probe_list = [] #keep track of requested probes
		dot_file = ['digraph G {\n\tsize ="96,96";\n\toverlap=scale;\n'] #start the graphviz config file
		for mac in (Clients):
			key = Clients[mac]
			for probe in key[6:]:
				if probe == '':
					pass
				else:
					Clients_list.append(key[0])
					if probe not in Probe_list:
						Probe_list.append(probe)
					dot_file.extend(dot_libs.graphviz_link(key[0],'->',probe))
		
		footer = ['label="Generated by Airgraph-ng','\\n%s'%(len(Clients_list)),' Clients and','\\n%s'%(len(Probe_list)),' Probes are shown";\n']
		return_list = [dot_file,footer]
		return return_list 

	def CAPR_main(info): #The Main Module for Client AP Relationship Grpah
		#info comes in a list Clients Dictionary at postion 0 and AP Dictionary at postion 1
		Clients = info[0]
		AP = info[1]
		dot_file = ['digraph G {\n\tsize ="96,96";\n\toverlap=scale;\n'] #start the graphviz config file
		NA = [] #create a var to keep the not associdated clients
		NAP = [] #create a var to keep track of associated clients to AP's we cant see
		AP_Count = {} # track the number of access points with clients connected and keep track of dumplicate lables
		Client_count = {} # count the number of clients dict is faster the list
		#color_trac = {} #track the colors of each AP

		for mac in (Clients):
			key = Clients[mac]
			if key[5] != "(notassociated)":
				if AP.has_key(key[5]): # does key look up in the Access point dictionary
					bssidI = AP[key[5]] # stores the correct bssid in the var
					essid = bssidI[13].rstrip('\x00') #when readidng a null essid it has binary space? so rstrip removes this 
					dot_file.extend(dot_libs.graphviz_link(key[5],'->',mac)) #call the libary function to create a basic link between the two devices
					#if Client_count.has_key(mac): #check to see if we have allready given the client a label
					#	pass
					#else:
					#	dot_file.extend(dot_libs.Client_Label_Color(mac,"Black")) #label the client with a name and a color right now all colors are black
					#	Client_count[mac] = mac #add our client to the list of labled clients
					if AP_Count.has_key(key[5]): #check to see if we have allready created a label for this access point
						pass
					else:
						color = dot_libs.Return_Enc_type(bssidI[5]) # Deterimine what color the graph should be 
						if bssidI[5] == '': #if there is no encryption detected we set it to unknown
							bssidI[5] = "Unknown"
						AP_label = [key[5],essid,bssidI[3],bssidI[5]]# Create a list with all our info to label the clients with
						dot_file.extend(dot_libs.AP_Label_Color(AP_label,color)) #create the label for the access point and return it to the dot file we are creating
						AP_Count[key[5]] = essid
					
					if Client_count.has_key(mac): #check to see if we have allready given the client a label
						pass
					else:
					        dot_file.extend(dot_libs.Client_Label_Color(mac,"black")) #label the client with a name and a color right now all colors are black
						Client_count[mac] = mac #add our client to the list of labled clients

				else:
					NAP.append(key) # stores the clients that are talking to an access point we cant see
			else: 
				NA.append(key) #stores the lines of the none assocated AP's in a list
		
		footer = ['label="Generated by Airgraph-ng','\\n%s'%(len(AP_Count)),' Access Points and','\\n%s'%(len(Client_count)),' Clients are shown";\n']
		return_list = [dot_file,footer,NAP,NA] # the chaft list is where we store all the lines that eneded up on the cutting room floor
		return return_list
                

	if graph_type == "CAPR":
		return_var = CAPR_main(info) #return_var is a list, dotfile postion 0, Not asscioated clients in  3 and Clients talking to access points we cant see 2, the footer in 1
		return_var = dot_libs.dot_close(return_var[0],return_var[1])
	elif graph_type == "CPG":
		return_var = CPG_main(info) #return_var is a list, dotfile postion 0, the footer in 1
		return_var = dot_libs.dot_close(return_var[0],return_var[1])
	elif graph_type == "ZKS":
		return_var = ZKS_main(info)
		return_var = dot_libs.dot_close(return_var[0],return_var[1])		
	
	return return_var	


def grpahviz_Call(output):
	print "Creating your Graph, Depending on your system this can take a bit. Please standby.............."
	try:
		subprocess.Popen(["fdp","-Tpng","airGconfig.dot","-o",output]).wait()
	except Exception:
		print "You seem to be missing the Graphviz tool set did you check out the deps in the read me?"
		sys.exit(1)
	subprocess.Popen(["rm","-rf","airGconfig.dot"])  # commenting out this line will leave the dot config file for debuging
	print "Graph Creation Complete!"
###################################
#              MAIN               #
###################################

if __name__ == "__main__":
	#graph_type = ''  #creats the graph type var so its declared
	if len(sys.argv) <= 1:
        	about()  #may not be needed
        	showBanner()
        	sys.exit(0)

        parser = optparse.OptionParser("usage: %prog [options] -i input -o output -g graph type .....")  #read up more on this
	parser.add_option("-o", "--output",  dest="output",nargs=1, help="Our Output Image ie... Image.png")
	parser.add_option("-i", "--dump", dest="input", nargs=1 ,help="Airodump txt file in CSV format NOT the pcap")
	parser.add_option("-g", "--graph", dest="graph_type", nargs=1 ,help="Choose the Graph Type Current types are [CAPR (Client to AP Relationship) & CPG (Common probe graph)]")
	(options, args) = parser.parse_args()
	filename = options.output
	graph_type = options.graph_type
	in_file = options.input
	
	#pdb.set_trace() #debug point
	if filename == None:
		print "You must choose an output file name"
		sys.exit(1)
	if graph_type not in ['CAPR','CPG','ZKS']:
		print "Error Invalid Graph Type\nVaild types are CAPR or CPG"
		sys.exit(1)
	if graph_type == '':
		print "Error No Graph Type Defined"
		sys.exit(1)
	#pdb.set_trace() #debug point
	returned_var = airDumpOpen(in_file)
	#pdb.set_trace() #debug point
	returned_var = airDumpParse(returned_var)
	#pdb.set_trace() #debut point	
	returned_var = dot_create(returned_var,graph_type)
	#pdb.set_trace() #debug point 
	dot_libs.dot_write(returned_var)
	grpahviz_Call(filename)
	
		

################################################################################
#                                     EOF                                      #
################################################################################
#notes windows port
#subprocess.Popen(["del","airGconfig.dot"])  # commenting out this line will leave the dot config file for debuging
#subprocess.Popen(["c:\\Program Files\\Graphviz2.21\\bin\\fdp.exe","-Tpng","airGconfig.dot","-o",output,"-Kfdp"]).wait(
