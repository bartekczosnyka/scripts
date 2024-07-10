import os
import re
import shutil
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright


class ServiceConfig:
    def __init__(self, name, clickable, octa_address, local_address, elements_to_restore):
        self.name = name
        self.clickable = clickable
        self.octa_address = octa_address
        self.local_address = local_address
        self.elements_to_restore = elements_to_restore

browser_dir = f"C:/Users/{os.getlogin()}/AppData/Local/Google/Chrome/User Data"
browser_channel = "chrome"
browser_executable_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"

def create_repo_path(suffix):
    return f"C:/Users/{os.getlogin()}/repos/shipstation/{suffix}"


web_V3_api_config = ServiceConfig(
    "WebV3Api",
    "WebV3Api.exe.config$", 
    "https://octoprod.sslocal.com/app#/Spaces-1/projects/v3-backend/deployments",
    create_repo_path("WebV3Api/App.config"), 
    ['V3QueueName', 'QueueName', 'QueueProviderType', 
     'SQSEndpoint', 'SQSEndpointHttps', 'SQSQueueBasePath', 
     'SQSQueueSuffix', 'RedisServer', 'RedisReplicaServers'])

V3_queue_service_config = ServiceConfig(
    "V3QueueService",
    "V3QueueService.exe.config$", 
    "https://octoprod.sslocal.com/app#/Spaces-1/projects/v3-backend/deployments", 
    create_repo_path("V3QueueService/App.config"), 
    ['V3QueueName', 'QueueName', 'QueueProviderType', 
     'SQSEndpoint', 'SQSEndpointHttps', 'SQSQueueBasePath', 
     'SQSQueueSuffix', 'RedisServer'])

job_service_config = ServiceConfig(
    "JobService",
    "JobService.exe.config$", 
    "https://octoprod.sslocal.com/app#/Spaces-1/projects/shipstation-services/deployments",
     create_repo_path("JobService/app.config"), 
    ['V3QueueName', 'QueueProviderType', 
     'SQSEndpoint', 'SQSEndpointHttps', 'SQSQueueBasePath', 
     'SQSQueueSuffix', 'RedisServer'])

order_service_config = ServiceConfig(
    "OrderService",
    "OrderService.exe.config$", 
    "https://octoprod.sslocal.com/app#/Spaces-1/projects/shipstation-services/deployments",
    create_repo_path("OrderService/app.config"), 
    ['V3QueueName', 'QueueProviderType', 
     'SQSEndpoint', 'SQSEndpointHttps', 'SQSQueueBasePath', 
     'SQSQueueSuffix', 'RedisServer',])

label_service_config = ServiceConfig(
    "LabelService",
    "LabelService.exe.config$", 
    "https://octoprod.sslocal.com/app#/Spaces-1/projects/shipstation-services/deployments",
    create_repo_path("LabelService/App.config"),
    ['V3QueueName', 'QueueProviderType', 
     'SQSEndpoint', 'SQSEndpointHttps', 'SQSQueueBasePath', 
     'SQSQueueSuffix', 'RedisServer', 'LabelOutputPath', 'LogPath'])


configs = [web_V3_api_config, V3_queue_service_config, job_service_config, order_service_config, label_service_config]

def get_values_based_on_keys(root, keys):
    dict = {}
    for key in keys:
        element = root.find(f'.//add[@key="{key}"]')
        if element is None:
            print(f"Could not find key: {key}.")
            continue
        value = element.get('value')
        dict[key] = value
    return dict

def get_page():
    context = sync_playwright().start()
    browser = context.chromium.launch_persistent_context(
        user_data_dir = browser_dir,
        # change to true if you want to see the browser working
        headless = True,
        channel = browser_channel,
        executable_path =  browser_executable_path,
        args = ["--start-maximized"]
    )
    return browser.new_page()

def print_message(message):
    print('----------------------------------')
    print(message)
    print('----------------------------------')

def set_configs():
    page = get_page()

    for config in configs:
        print_message(f"Starting to update {config.name} config...")
        
        page.goto(config.octa_address)

        try:
            # the easiest way to find the Z deployment
            page.get_by_text("Integration Channel").click()

            with page.expect_download() as download_info:
                webv3ApiConfigLink = page.get_by_text(re.compile(config.clickable)).first
                webv3ApiConfigLink.click()

            local_config_tree = ET.parse(config.local_address)
            local_config_root = local_config_tree.getroot()

            shutil.copy(download_info.value.path(), config.local_address)   

            local_config_tree_after_copied = ET.parse(config.local_address)
            local_config_root_after_copied = local_config_tree_after_copied.getroot()

            # restore values from old config to new one
            elements_to_restore = get_values_based_on_keys(local_config_root, config.elements_to_restore)
            for key, value in elements_to_restore.items():
                try:
                    element = local_config_root_after_copied.find(f'.//add[@key="{key}"]')
                    print(f"Updating {key} to {value}")
                    element.set('value', value)
                except Exception as e:
                    print(f"Could not updated key: {key} with value: {value}.")
                    print(e)
            # remove runtime element from config
            # for some reason it is added to the config after copying
            local_config_root_after_copied.remove(local_config_root_after_copied.find(f'.//runtime'))
            # write updated config
            local_config_tree_after_copied.write(config.local_address, encoding="utf-8", xml_declaration=True)

            print_message(f"Updated {config.name} config.")
            print('\n')
        except Exception as e:
            print_message(f"Could not update {config.name} config because of error {e}")
            print('\n')


if __name__ == "__main__":
    print("In order to run this script we need to kill all chrome processes.")
    print("Do you want to continue? (y/n)")
    answer = input()
    if answer.lower() == 'y':
        os.system("taskkill /F /IM chrome.exe")
        set_configs()
    print("Exiting...")
    exit()
