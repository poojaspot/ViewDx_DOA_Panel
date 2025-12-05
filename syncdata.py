from dataconnector import DataConnector
import results
import json
import subprocess
import widgets


#to be added within the screen call of wherever the sync button is
def syncdata():
    online = subprocess.call(["ping","-c","1","8.8.8.8"], stdout = subprocess.DEVNULL)==0
    print(online)
    if not online:
        widgets.error("Please connect the WIFI and try again")
        return
    
    connector = DataConnector(config_path="config.json")
    result = connector.syncdata(json_path="/home/pi/viewdx/results/results.json",
                                hl7_path="")
    print("=====Sync result=====")
    print(json.dumps(result, indent=2))
    if "json" in result:
        if "error" in result["json"]:
            print("json push failed:", result["json"]["error"])
        else:
            print("json push OK (status", result["json"]["status_code"],")")
            print("response", result["json"]["response_text"])
    if "hl7" in result:
        if "error" in result["hl7"]:
            print("HL7 push failed:", result["hl7"]["error"])
        else:
            print("hl7 push of (status", reuslt["hl7"]["status_code"],")")
            print("Response:", result["hl7"]["response_test"])
            


# syncdata()


# if __name__ == "__main__":
#     result = syncdata()
#     print(json.dumps(result, indent=2))