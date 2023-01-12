from re import I
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from paramiko import client as paramiko
from datetime import date
from decimal import Decimal
import os
import sys
import json
import configparser

datas = {}
mcrs3 = {}
CONFIG = configparser.ConfigParser()
PRIDEX_INPUTS = {}


def Open_chrome_driver():
    # chrome = init_chrome_driver()
    options = Options()
    options.add_argument("user-data-dir=" + CONFIG["config"]["GOOGLE_USER_PATH"])
    options.add_argument("profile-directory=Default")
    chrome = webdriver.Chrome(
        os.path.join(get_app_path(), "chromedriver.exe"), options=options
    )
    chrome.get(CONFIG["config"]["MWT_ROUTINE_ADRESS"])
    return chrome
    # WebDriverWait(chrome, 180).until(EC.visibility_of_element_located((By.XPATH,'//span[text()="Next "]')))


def get_config_datas():
    global PRIDEX_INPUTS
    CONFIG.read("config.ini")
    PRIDEX_INPUTS = json.loads(CONFIG.get("config", "PRIDEX_INPUTS"))


def get_app_path():
    # determine if application is a script file or frozen exe
    if getattr(sys, "frozen", False):
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        application_path = os.path.dirname(__file__)

    return application_path


def get_data():
    if yes_or_no("Blask has finished ?"):
        raw_datas = read_file()
        if len(raw_datas) != 0:
            extract_data(raw_datas)
        else:
            print("Error reading the result file. Application will exit")
            quit()


def read_file():
    lines = []
    try:
        with open(CONFIG["config"]["RESULT_LOCATION"]) as f:
            lines = f.readlines()
    except:
        print("Error reading the result file. Application will exit")
        quit()
    return lines


def extract_data(raw_datas):
    for data_line in raw_datas:
        try:
            if " = " in data_line:
                splited_line = data_line.split(" = ")
                datas[splited_line[0]] = splited_line[1].replace("\n", "")
        except:
            print("Value not retrieved from result :" + data_line)


def send_data_to_pridex(chrome):
    for data_key in datas:
        try:
            mat_label_elem = chrome.find_element(
                By.XPATH, '//mat-label[text()="' + PRIDEX_INPUTS[data_key] + '"]'
            )
            label_parent_elem = mat_label_elem.find_element(By.XPATH, "..")
            span_parent_elem = label_parent_elem.find_element(By.XPATH, "..")
            div_parent_elem = span_parent_elem.find_element(By.XPATH, "..")
            input_elem = div_parent_elem.find_element(By.TAG_NAME, "input")
            input_elem.send_keys(datas[data_key])
        except:
            pass

    print(mcrs3["IcGain"])
    print(mcrs3["Mean Charge"])
    print(mcrs3["Charge Sigma"])

    while True:
        if yes_or_no("Did you finish your MWT and save the data ?"):
            break


def yes_or_no(question):
    reply = str(input(question + " (y/n): ")).lower().strip()
    if reply[0] == "y":
        return 1
    elif reply[0] == "n":
        return 0
    else:
        return yes_or_no("Please Enter (y/n) ")


def init_chrome_driver():
    s = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("start-maximized")
    # to supress the error messages/logs
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    driver = webdriver.Chrome(service=s, options=options)
    return driver


def get_date_formated():
    today = date.today()
    year = str(today.year)
    month = str(today.month)
    day = str(today.day)

    if len(month) < 2:
        month = "0" + month
    if len(day) < 2:
        day = "0" + day

    return year + month + day


def access_mcrs3():
    lookup_filename_patern = CONFIG["config"]["SITE_NAME"] + "_" + get_date_formated()
    lookup_filename = ""
    try:
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            CONFIG["config"]["MCRS3_HOSTNAME"],
            CONFIG["config"]["MCRS3_SSH_PORT"],
            CONFIG["config"]["MCRS3_USER"],
            CONFIG["config"]["MCRS3_PWD"],
        )
        sftp = client.open_sftp()
        files = sftp.listdir(CONFIG["config"]["LOOKUP_PATH"])
        lookuptimes = []
        for filename in files:
            if lookup_filename_patern in filename and "failed" not in filename:
                lookuptimes.append(filename.split("_")[2].replace(".csv", ""))

        lastlookuptime = max(lookuptimes)
        lookup_filename = [lookup for lookup in files if lastlookuptime in lookup]
        if len(lookup_filename) > 0:
            lookup_filename = files[0]

        if lookup_filename != "":
            fileObject = sftp.file(
                CONFIG["config"]["LOOKUP_PATH"] + "/" + lookup_filename, "r"
            )
            found_var = 0

            for line in fileObject:
                if "IcGain" in line:
                    try:
                        temp_data = line.split(",")
                        mcrs3["IcGain"] = (
                            temp_data[len(temp_data) - 1]
                            .split("=")[1]
                            .replace("\n", "")
                        )
                        found_var += 1
                    except:
                        pass
                elif "100.000," in line:
                    try:
                        temp_data = line.split(",")
                        mcrs3["Mean Charge"] = temp_data[1].replace("\n", "")
                        mcrs3["Mean Charge"] = str(
                            Decimal(mcrs3["Mean Charge"]) * 1000000000000
                        )
                        mcrs3["Charge Sigma"] = temp_data[2].replace("\n", "")
                        mcrs3["Charge Sigma"] = str(
                            Decimal(mcrs3["Charge Sigma"]) * 1000000000000
                        )
                        found_var += 1
                    except:
                        pass

                if found_var > 1:
                    break

        fileObject.close()
        sftp.close()
    except:
        pass


def main():
    get_config_datas()
    chrome = Open_chrome_driver()
    get_data()
    access_mcrs3()
    send_data_to_pridex(chrome)
    os.remove(CONFIG["config"]["RESULT_LOCATION"])


main()
