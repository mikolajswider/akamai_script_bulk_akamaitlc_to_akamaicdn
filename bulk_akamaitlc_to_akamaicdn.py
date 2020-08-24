
#!/usr/bin/python3

import os
import subprocess
import time
import socket
import shlex
import re
import requests
from akamai.edgegrid import EdgeGridAuth
import json # library needed for json manipulation

"""
The following script was created to replace gracefully AKAMAITLC records by AKAMAICDN records, in bulk, for a given customer's account.\n
Domains are being provided via the input.txt file.\n
This file is being parsed and for each and every domain, the following is being done:\n
 1) A dig command is being issue in order to retrieve all available IP addresses.\n
 2) The AKAMAITLC record is being parsed and its content stored.\n
 3) An A record is being created based on the previously issued dig command.\n
 4) The old AKAMAITLC record is being deleted.\n
 5) The new AKAMAICDN record is being created based on the old AKAMAITLC record.\n
 6) The A record initially created is being deleted.\n
Note: If a given operation fails, then the next steps are discontinued.\n
\n
Before using this script, make sure that:\n
 a) API credentials have been copied to the api_creds.txt file.\n
 b) The switchkey parameter associated with the customer's account has been copied to the switchkey_ref.txt file.\n
\n
Contributors:\n
- Kasia (kszmyd) as Chief Ideator\n
- Miko (mswider) as Chief Programmer\n
\n bulk_akamaitlc_to_akamaicdn v1.0
"""

def main() -> None:
        # intructions
        print("""\nThe following script was created to replace gracefully AKAMAITLC records by AKAMAICDN records, in bulk, for a given customer's account. \nDomains are being provided via the input.txt file. \nThis file is being parsed and for each and every domain, the following is being done:\n 1) A dig command is being issue in order to retrieve all available IP addresses.\n 2) The AKAMAITLC record is being parsed and its content stored. \n 3) An A record is being created based on the previously issued dig command.\n 4) The old AKAMAITLC record is being deleted. \n 5) The new AKAMAICDN record is being created based on the old AKAMAITLC record. \n 6) The A record initially created is being deleted. \nNote: If a given operation fails, then the next steps are discontinued. \n """)
        input("Before using this script, make sure that: \n a) API credentials have been copied to the api_creds.txt file. \n b) The switchkey parameter associated with the customer's account has been copied to the switchkey_ref.txt file. \n\nPress any key to continue.")
        
        # opening API credential file and preparing base url and credentials for http requests
        api_cred_file = open('api_creds.txt','r', encoding='utf-8')
        for line in api_cred_file:
            line = str(line.strip())    
            if line.startswith("client_token"):
                client_token = line[15:]    
            if line.startswith("client_secret"):
                client_secret = line[16:]
            if line.startswith("access_token"):
                access_token = line[15:]
            if line.startswith("host"):
                host = line[7:]
        #print (client_secret)
        #print (host)
        #print (access_token)
        #print (client_token)

        # opening switchekey_ref.txt file and extracting the switchkey parameter
        switchkey_ref_file = open('switchkey_ref.txt', 'r', encoding='utf-8')        
        for line in switchkey_ref_file:
            switchkey = str(line.strip())
        #print(switchkey)

        # creating a folder named "domains" in current directory
        #subprocess.call(['mkdir', 'domains'])
        
        # reading the input.txt file with domain names
        input_file = open('input.txt','r', encoding='utf-8')

        # parsing input file and for each domain creating, deleting and reading DNS records in FAST DNS configuration
        for domain in input_file:
            domain = str(domain.strip())
            print("Starting to process " + domain + ".")
            path = "domains/" + domain

            # issuing a dig command for a given domain
            command = 'dig A '+ domain + ' +short' #bash dig command
            #domain_file = open(path,'w+', encoding='utf-8') #creating a file 
            raw_records = str(subprocess.check_output(shlex.split(command))) #DNS A record/records obtained by issuing a dig command
            ip_address = r'(?:[\d]{1,3})\.(?:[\d]{1,3})\.(?:[\d]{1,3})\.(?:[\d]{1,3})' #regex matching IP addresses
            ip_list = re.findall(ip_address, raw_records)
            #print(ip_list)
            if ip_list!=[]:
                print("Dig command issued successfully for " + domain + ".")
                #domain_file.write(str(ip_list))

                # get AKAMAITLC record
                http_response = api_record_get(domain, domain, "AKAMAITLC", host, client_secret, access_token, client_token, switchkey)
                code = http_response.status_code
                content = http_response.content
                print(content)
                if code == 200:
                    print("AKAMAITLC record exists for "+domain+", and was successfully retrieved.")
                    akamaitlc = (eval(http_response.text))['rdata']                    
                    #print(akamaitlc)
                    akamaicdn=[]
                    for entry in akamaitlc:
                        if entry.startswith("A "):
                            akamaicdn=akamaicdn+[entry[2:]]
                        if entry.startswith("AAAA "):
                            akamaicdn=akamaicdn+[entry[5:]]
                        if entry.startswith("DUAL "):
                            akamaicdn=akamaicdn+[entry[5:]]
                    #print(akamaicdn)

                    # post A record to zone
                    http_response = api_record_create(domain, domain, "A", host, client_secret, access_token, client_token, switchkey, ip_list, 30)
                    code = http_response.status_code
                    content = http_response.content
                    #print(code)
                    print(content)
                    if code == 201:
                        print("A record for " + domain +  " was successfully created.")
                        
                        # delete AKAMAITLC record
                        http_response = api_record_del(domain, domain, "AKAMAITLC", host, client_secret, access_token, client_token, switchkey)
                        code = http_response.status_code
                        content = http_response.content
                        #print(code)
                        print(content)
                        if code == 204:
                            print("AKAMAITLC record for "+domain+", was successfully deleted.")
                            
                            # post AKAMAICDN record
                            http_response = api_record_create(domain, domain, "AKAMAICDN", host, client_secret, access_token, client_token, switchkey, akamaicdn, 20)
                            code = http_response.status_code
                            content = http_response.content
                            #print(code)
                            print(content)
                            if code == 201:
                                print("AKAMAICDN record for " + domain +  " was successfully created.")

                                # delete A record previously created
                                http_response = api_record_del(domain, domain, "A", host, client_secret, access_token, client_token, switchkey)
                                code = http_response.status_code
                                content = http_response.content
                                #print(code)
                                print(content)
                                if code == 204:
                                    print("A record for "+domain+", was successfully deleted.")
                                    input("Finished processing " + domain + " successfully. \n \nPress any key to continue.")

                                else:
                                    print("A record for " + domain +  " was not deleted. Not proceeding further.\n")
                                    input("Press any key to continue.")

                            else:
                                print("AKAMAICDN record for " + domain +  " was not created. Not proceeding further.\n")
                                input("Press any key to continue.")

                        else:
                            print("AKAMAITLC record for "+domain+", was not deleted. Not proceeding further.\n")
                            input("Press any key to continue.")

                    elif code == 409:
                        print("An A record already exists for "+ domain +". Not proceeding further.\n")
                        input("Press any key to continue.")

                    else:
                        print("A new A record could not be created for "+ domain +". Not proceeding further.\n")
                        input("Press any key to continue.")
                else: 
                    print("No AKAMAITLC record found for "+domain+". Not proceeding further.\n")
                    input("Press any key to continue.")
            else:
                print("Dig command issued unsuccessfully for "+domain+". Not proceeding further.\n")
                input("Press any key to continue.")        
            #domain_file.close()

        input_file.close()
  
        #subprocess.call(['rm','-r', 'domains'])
        print ("input.txt was entirely parsed. Ending operations.\n")

# api_record_get is a function used to issue an API call https://developer.akamai.com/api/web_performance/fast_dns_zone_management/v2.html#getzonerecordset
def api_record_get(zone: str, name: str, type: str, host:str, client_secret: str, access_token: str, client_token: str, switchkey: str):
    url = 'https://'+host+'/config-dns/v2/zones/' + zone + '/names/' + name + '/types/'+type+'?accountSwitchKey='+switchkey
    #print(url)
    # creating a http request
    http_request = requests.Session()
    http_request.auth = EdgeGridAuth(client_token, client_secret, access_token)
    http_response = http_request.get(url)
    #print(http_response.status_code)
    #print(http_response.content)
    return(http_response)

# api_record_del is a function used to issue an API call https://developer.akamai.com/api/web_performance/fast_dns_zone_management/v2.html#deletezonerecordset
def api_record_del(zone: str, name: str, type: str, host:str, client_secret: str, access_token: str, client_token: str, switchkey: str):
    url = 'https://'+host+'/config-dns/v2/zones/' + zone + '/names/' + name + '/types/'+type+'?accountSwitchKey='+switchkey
    #print(url)
    # creating a http request
    http_request = requests.Session()
    http_request.auth = EdgeGridAuth(client_token, client_secret, access_token)
    http_response = http_request.delete(url)
    #print(http_response.status_code)
    #print(http_response.content)
    return(http_response)


# api_record_create is a function used to issue an API call https://developer.akamai.com/api/web_performance/fast_dns_zone_management/v2.html#postzonerecordset
def api_record_create(zone: str, name: str, type: str, host:str, client_secret: str, access_token: str, client_token: str, switchkey: str, ip_list: list, ttl: int):
    url = 'https://'+host+'/config-dns/v2/zones/' + zone + '/names/' + name + '/types/'+type+'?accountSwitchKey='+switchkey
    #print(url)

    # creating a http request
    http_request = requests.Session()
    
    # post request headers
    http_request.auth = EdgeGridAuth(client_token, client_secret, access_token)
    headers ={}
    headers['Content-type']="application/json"
    http_request.headers = headers

    # defining body of post request
    body = {}
    body['name'] = name
    body['type'] = type
    body['ttl'] = ttl
    body['rdata'] = ip_list
    #print(body)
    json_body = json.dumps(body)
    #print(json_body)
    #http_request.data = json_body
    http_response = http_request.post(url, data=json_body)
    return(http_response)

if __name__ == '__main__':
    main()
