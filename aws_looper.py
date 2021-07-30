#!/usr/bin/env python3
# Simple script to rotate a command through all AWS applications by adding keys to your environment variables

import requests
import subprocess
import pathlib
import argparse


def main():

    role, app_list, app_single, command, token, awspx, scoutsuite = cli()
    if app_single is None:
        apps = list_parser(app_list)
    elif app_list is None and app_single is not None:
        apps = app_single
    else:
        print("Oops, something's broke!")
        exit()

    for app in apps:
        app = app.split(',', 1)
        access_key, secret_key, session_key = request(token, app[0], role)
        run_command(access_key, secret_key, session_key, awspx, scoutsuite, command, app[1])

def cli():
    """
    Argument Parser for CLI commands.
    Returns Term, Location (default none)
    """
    parser=argparse.ArgumentParser(
        description = 'Rotate through a given AWS account for per application keys.  Keys are temporarily loaded into environment variables.  Asks for a SSO cookie value.')
    parser.add_argument('role', help = 'Role to harvest session keys as')
    parser.add_argument(
        '-c', '--command', help = 'Custom command to run.', default = None)
    parser.add_argument('-a', '--application',
                        help = 'Provide a specific application', default = None)
    parser.add_argument(
        '-l', '--list', help = 'Provide a list of applications.  Lists should be one Application#,Application Name per line', default = None)
    parser.add_argument(
        '-p', '--awspx', help = 'Run awspx across all applications.  Install from https://github.com/FSecureLABS/awspx', action=argparse.BooleanOptionalAction, default = False)
    parser.add_argument(
        '-s', '--scoutsuite', help = 'Run ScoutSuite across all applications.  Install from https://github.com/nccgroup/ScoutSuite', action=argparse.BooleanOptionalAction, default = False)
    args=parser.parse_args()

    print("Please provide an SSO cookie value.  Obtain from the dev console on a web browser, probably named something like x-amz-sso_authn")
    token=input()

    return args.role, args.list, args.application, args.command, token, args.awspx, args.scoutsuite


def request(bearer_token, account_id, role_name):
    # NB. Original query string below. It seems impossible to parse and
    # reproduce query strings 100% accurately so the one below is given
    # in case the reproduced version is not "correct".
    # response = requests.get('https://portal.sso.us-east-1.amazonaws.com/federation/credentials/?account_id=${account_id}&role_name=${role_name}&debug=true', headers=headers)

    headers={
        'authority': 'portal.sso.us-east-1.amazonaws.com',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="90", "Microsoft Edge";v="90"',
        'accept': 'application/json, text/plain, */*',
        'x-amz-sso_bearer_token': f"{bearer_token}",
        'sec-ch-ua-mobile': '?0',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36 Edg/90.0.818.49',
        'p3p': 'policyref="https://www.amazon.com/w3c/p3p.xml", CP="CAO DSP LAW CUR ADM IVAo IVDo CONo OTPo OUR DELi PUBi OTRi BUS PHY ONL UNI PUR FIN COM NAV INT DEM CNT STA HEA PRE LOC GOV OTC"',
        'origin': 'https://dynatasso.awsapps.com',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://dynatasso.awsapps.com/',
        'accept-language': 'en-US,en;q=0.9',
    }

    params = (
        ('account_id', f"{account_id}"),
        ('role_name', f"{role_name}"),
        ('debug', 'true'),
    )

    response=requests.get(
        'https://portal.sso.us-east-1.amazonaws.com/federation/credentials/', headers = headers, params = params)

    access_key=response.json()["roleCredentials"]['accessKeyId']
    secret_key=response.json()["roleCredentials"]['secretAccessKey']
    session_key=response.json()["roleCredentials"]['sessionToken']
    return access_key, secret_key, session_key

def run_command(access_key, secret_key, session_key, awspx, scoutsuite, command, app):
        if awspx is True:
            command = f"awspx ingest --env --database {app}.db"
        elif scoutsuite is True:
            command = 'python scoute.py aws'
        else:
            command = command

        
        print("Running '" + command + "' on application " + app)
        #aws_env = ['AWS_ACCESS_KEY_ID=' + access_key, 'AWS_SECRET_ACCESS_KEY=' + secret_key, 'AWS_SESSION_TOKEN=' + session_key]
        aws_env = {'AWS_ACCESS_KEY_ID' : access_key, 'AWS_SECRET_ACCESS_KEY' : secret_key, 'AWS_SESSION_TOKEN' : session_key}
        subprocess.run(command, env = aws_env, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)


def list_parser(file_in):
    try:
        f=pathlib.Path(file_in)
        return f.read_text().split('\n')

    except IOError:
        return False, None


if __name__ == '__main__':
    main()
