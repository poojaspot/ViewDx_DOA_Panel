import requests
import socket
import subprocess
from urllib.parse import urlparse
import json
import os

class DataConnector:
    def __init__(self, config_path="config.json"):
        self.config = self.load_config(config_path)

    def load_config(self, config_path):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file {config_path} not found")
        with open(config_path, "r") as f:
            return json.loads(f.read())
    
    def validate_config(self):
        required = ["endpoint","auth_type","headers"]
        for key in required:
            if not self.config.get(key):
                raise ValueError(f"Missing required config: {key}")
        endpoint = self.config.get("endpoint")
        parsed = urlparse(endpoint)
        if parsed.scheme not in ("http","https"):
            raise ValueError(f"Invalid endpoint scheme: {endpoint}")
        if not parsed.netloc:
            raise ValueError(f"Invalid endpoint host: {endpoint}")
        host = parsed.hostname
        try:
            print(f"Pinging {host}...")
            result = subprocess.call(["ping","-c","1",host],
                                        stdout = subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            if result != 0:
                raise ValueError(f'Cannot reach endpoint host:{host}')
            else:
                print(f"Endpoint {host} is reachable")
        except Exception as e:
            raise ValueError(f"Ping check failed for {host}: {e}")
        try:
            print(f"Sending HEAD request to {endpoint} ...")
            resp = requests.head(endpoint, timeout=5)
            if resp.status_code >= 400:
                raise ValueError(f"Endpoint not healthy (status {resp.status_code})")
            print(f"Endpoint responded with {resp.status_code}")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Endpoint check failed: {e}")
        

        if self.config["auth_type"] == "basic":
            if not self.config.get("username") or not self.config.get("password"):
                raise ValueError("Basic auth requires username and password")
        elif self.config['auth_type'] =="api_key":
            raise ValueError("API key auth requires 'api_key' in config")
        headers = self.config.get("headers", {})
        if not isinstance(headers, dict):
            raise ValueError("Headers must be a dictionary")
        if not self.config.get("sync_mode"):
            self.config["sync_mode"] = "both" #sync both .json and hl7
            

    def push_json(self, json_path):
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Error: results.JSON file not found at {json_path}")
        with open(json_path, "r") as f:
            data = json.loads(f.read())
        headers = {"Content-Type": "application/json"}
        return self._post(data, headers)

    def push_hl7(self, hl7_path):
        if not os.path.exists(hl7_path):
            raise FileNotFoundError(f"HL7 file not found at {hl7_path}")
        with open(hl7_path, "r") as f:
            data = f.read()
        headers = {"Content-Type": "application/hl7-v2+er7"}
        return self._post(data, headers)

    def _post(self, data, headers):
        endpoint = self.config["endpoint"]
        auth_type = self.config.get("auth_type")
        username = self.config.get("username")
        password = self.config.get("password")
        api_key = self.config.get("api_key")
        
        try:
            if auth_type == "api_key" and api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                if isinstance(data,dict):
                    response = requests.post(endpoint, headers= headers, json=data , timeout=120)
                else:
                    response = requests.post(endpoint, headers= headers, data=data , timeout=120)

            elif auth_type == "basic" and username and password:
                if isinstance(data,dict):
                    response = requests.post(endpoint, headers= headers, json=data, auth=(username, password), timeout=120)
                else:
                    response = requests.post(endpoint, headers= headers, data=data,auth=(username, password), timeout=120)
            elif auth_type == "none":
                if isinstance(data,dict):
                    response = requests.post(endpoint, headers= headers, json=data, auth=(username, password), timeout=120)
                else:
                    response = requests.post(endpoint, headers= headers, data=data,auth=(username, password), timeout=120)
                pass
            else:
                raise Exception("Unsupported auth type.")
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")
        

    def syncdata(self, json_path, hl7_path):
        responses = {}
        sync_mode = self.config.get("sync_mode", "both")  # json, hl7, both
        if sync_mode in ("json", "both"):
            try:
                response = self.push_json(json_path)
                responses['json'] = {
                    'status_code': response.status_code,
                    'response_text': response.text
                }
            except Exception as e:
                responses['json'] = {'error': str(e)}

        if sync_mode in ("hl7", "both"):
            try:
                response = self.push_hl7(hl7_path)
                responses['hl7'] = {
                    'status_code': response.status_code,
                    'response_text': response.text
                }
            except Exception as e:
                responses['hl7'] = {'error': str(e)}
        return responses
