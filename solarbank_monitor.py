#!/usr/bin/env python
"""Example exec module to use the Anker API for continously querying and displaying important solarbank parameters
This module will prompt for the Anker account details if not pre-set in the header.
Upon successfull authentication, you will see the solarbank parameters displayed and refreshed at reqular interval.
Note: When the system owning account is used, more details for the solarbank can be queried and displayed.
Attention: During executiion of this module, the used account cannot be used in the Anker App since it will be kicked out on each refresh.
"""  # noqa: D205

import asyncio
from datetime import datetime, timedelta
from getpass import getpass
import json
import logging
import os
import sys
import time

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from api import api, errors

_LOGGER: logging.Logger = logging.getLogger(__name__)
_LOGGER.addHandler(logging.StreamHandler(sys.stdout))
# _LOGGER.setLevel(logging.DEBUG)    # enable for debug output
CONSOLE: logging.Logger = logging.getLogger("console")
CONSOLE.addHandler(logging.StreamHandler(sys.stdout))
CONSOLE.setLevel(logging.INFO)

# Optional default Anker Account credentials to be used
USER = ""
PASSWORD = ""
COUNTRY = ""
REFRESH = 30  # default refresh interval in seconds


def clearscreen():
    """Clear the terminal screen."""
    if sys.stdin is sys.__stdin__:  # check if not in IDLE shell
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")
        # CONSOLE.info("\033[H\033[2J", end="")  # ESC characters to clear terminal screen, system independent?


def get_subfolders(folder: str) -> list:
    """Get the full pathnames of all subfolders for given folder as list."""
    if os.path.isdir(folder):
        return [os.path.abspath(f) for f in os.scandir(folder) if f.is_dir()]
    return []


async def main() -> None:  # noqa: C901
    """Run Main routine to start Solarbank monitor in a loop."""
    global USER, PASSWORD, COUNTRY, REFRESH  # noqa: W0603, PLW0603
    CONSOLE.info("Solarbank Monitor:")
    # get list of possible example and export folders to test the monitor against
    exampleslist = get_subfolders(
        os.path.join(os.path.dirname(__file__), "examples")
    ) + get_subfolders(os.path.join(os.path.dirname(__file__), "exports"))
    if USER == "":
        if exampleslist:
            CONSOLE.info("\nSelect the input source for the monitor:")
            CONSOLE.info("(0) Real time from Anker cloud")
            for idx, filename in enumerate(exampleslist, start=1):
                CONSOLE.info("(%s) %s", idx, filename)
        selection = input(f"Input Source number (0-{len(exampleslist)}): ")
        if (
            not selection.isdigit()
            or int(selection) < 0
            or int(selection) > len(exampleslist)
        ):
            return False
        if (selection := int(selection)) == 0:
            use_file = False
            CONSOLE.info("\nEnter Anker Account credentials:")
            USER = input("Username (email): ")
            if USER == "":
                return False
            PASSWORD = getpass("Password: ")
            if PASSWORD == "":
                return False
            COUNTRY = input("Country ID (e.g. DE): ")
            if COUNTRY == "":
                return False
        else:
            use_file = True
            testfolder = exampleslist[selection - 1]
    try:
        async with ClientSession() as websession:
            myapi = api.AnkerSolixApi(USER, PASSWORD, COUNTRY, websession, _LOGGER)
            if use_file:
                # set the correct test folder for Api
                myapi.testDir(testfolder)
            elif await myapi.async_authenticate():
                CONSOLE.info("Anker Cloud authentication: OK")
            else:
                # Login validation will be done during first API call
                CONSOLE.info("Anker Cloud authentication: CACHED")

            while True:
                resp = input(
                    f"\nHow many seconds refresh interval should be used? (10-600, default: {REFRESH}): "
                )
                if not resp:
                    break
                elif resp.isdigit() and 10 <= int(resp) <= 600:
                    REFRESH = int(resp)
                    break

            # Run loop to update Solarbank parameters
            now = datetime.now().astimezone()
            next_refr = now
            next_dev_refr = now
            col1 = 15
            col2 = 20
            t1 = 2
            t2 = 5
            t3 = 5
            t4 = 9
            t5 = 6
            t6 = 10
            while True:
                CONSOLE.info("\n")
                now = datetime.now().astimezone()
                if next_refr <= now:
                    CONSOLE.info("Running site refresh...")
                    await myapi.update_sites(fromFile=use_file)
                    next_refr = now + timedelta(seconds=REFRESH)
                if next_dev_refr <= now:
                    CONSOLE.info("Running device details refresh...")
                    await myapi.update_device_details(fromFile=use_file)
                    next_dev_refr = next_refr + timedelta(seconds=REFRESH * 9)
                    # schedules = {}
                clearscreen()
                CONSOLE.info(
                    f"Solarbank Monitor (refresh {REFRESH} s, details refresh {10*REFRESH} s):"
                )
                if use_file:
                    CONSOLE.info(f"Using input source folder: {myapi.testDir()}")
                CONSOLE.info(
                    f"Sites: {len(myapi.sites)}, Devices: {len(myapi.devices)}"
                )
                for sn, dev in myapi.devices.items():
                    devtype = dev.get("type", "Unknown")
                    admin = dev.get("is_admin", False)
                    CONSOLE.info(
                        f"{'Device':<{col1}}: {(dev.get('name','NoName')):<{col2}} (Alias: {dev.get('alias','Unknown')})"
                    )
                    CONSOLE.info(
                        f"{'SN':<{col1}}: {sn:<{col2}} (Admin: {'YES' if admin else 'NO'})"
                    )
                    CONSOLE.info(
                        f"{'PN':<{col1}}: {dev.get('device_pn',''):<{col2}} (Type: {devtype.capitalize()})"
                    )
                    if devtype == "solarbank":
                        siteid = dev.get("site_id", "")
                        CONSOLE.info(f"{'Site ID':<{col1}}: {siteid}")
                        CONSOLE.info(
                            f"{'Wifi SSID':<{col1}}: {dev.get('wifi_name',''):<{col2}}"
                        )
                        online = dev.get("wifi_online")
                        CONSOLE.info(
                            f"{'Wifi state':<{col1}}: {('Unknown' if online is None else 'Online' if online else 'Offline'):<{col2}} (Signal: {dev.get('wifi_signal','---')} %)"
                        )
                        upgrade = dev.get("auto_upgrade")
                        CONSOLE.info(
                            f"{'SW Version':<{col1}}: {dev.get('sw_version','Unknown'):<{col2}} (Auto-Upgrade: {'Unknown' if upgrade is None else 'Enabled' if upgrade else 'Disabled'})"
                        )
                        soc = f"{dev.get('battery_soc','---'):>3} %"
                        CONSOLE.info(
                            f"{'Status':<{col1}}: {dev.get('status_desc','Unknown'):<{col2}} (Status code: {str(dev.get('status','-'))})"
                        )
                        CONSOLE.info(
                            f"{'Charge Status':<{col1}}: {dev.get('charging_status_desc','Unknown'):<{col2}} (Status code: {str(dev.get('charging_status','-'))})"
                        )
                        CONSOLE.info(
                            f"{'State Of Charge':<{col1}}: {soc:<{col2}} (Min SOC: {str(dev.get('power_cutoff','--'))+' %'})"
                        )
                        unit = dev.get("power_unit", "W")
                        CONSOLE.info(
                            f"{'Solar Power':<{col1}}: {dev.get('input_power',''):>3} {unit:<{col2-4}} Charge Power: {dev.get('charging_power',''):>3} {unit}"
                        )
                        preset = dev.get("set_output_power") or "---"
                        CONSOLE.info(
                            f"{'Output Power':<{col1}}: {dev.get('output_power',''):>3} {unit:<{col2-4}} (Output Preset: {preset:>3} {unit})"
                        )
                        # update schedule with device details refresh and print it
                        if admin:
                            # Schedule is now included in the device details
                            # if not schedules.get(sn) and siteid:
                            #     schedules.update({sn: await myapi.get_device_load(siteId=siteid,deviceSn=sn,fromFile=use_file)})
                            # data = schedules.get(sn,{})
                            data = dev.get("schedule", {})
                            CONSOLE.info(
                                f"{'Schedule':<{col1}}: {now.strftime('%H:%M UTC %z'):<{col2}} (Current Preset: {(data.get('current_home_load','---')).replace('W','')} W)"
                            )
                            CONSOLE.info(
                                f"{'ID':<{t1}} {'Start':<{t2}} {'End':<{t3}} {'Discharge':<{t4}} {'Output':<{t5}} {'ChargePrio':<{t6}}"
                            )
                            # for slot in (data.get("home_load_data",{})).get("ranges",[]):
                            for slot in data.get("ranges", []):
                                enabled = slot.get("turn_on")
                                load = slot.get("appliance_loads", [])
                                load = load[0] if len(load) > 0 else {}
                                CONSOLE.info(
                                    f"{str(slot.get('id','')):>{t1}} {slot.get('start_time',''):<{t2}} {slot.get('end_time',''):<{t3}} {('---' if enabled is None else 'YES' if enabled else 'NO'):^{t4}} {str(load.get('power',''))+' W':>{t5}} {str(slot.get('charge_priority',''))+' %':>{t6}}"
                                )
                    elif devtype == "inverter":
                        siteid = dev.get("site_id", "")
                        CONSOLE.info(f"{'Site ID':<{col1}}: {siteid}")
                        CONSOLE.info(
                            f"{'Wifi SSID':<{col1}}: {dev.get('wifi_name',''):<{col2}}"
                        )
                        online = dev.get("wifi_online")
                        CONSOLE.info(
                            f"{'Wifi state':<{col1}}: {('Unknown' if online is None else 'Online' if online else 'Offline'):<{col2}} (Signal: {dev.get('wifi_signal','---')} %)"
                        )
                        upgrade = dev.get("auto_upgrade")
                        CONSOLE.info(
                            f"{'SW Version':<{col1}}: {dev.get('sw_version','Unknown'):<{col2}} (Auto-Upgrade: {'Unknown' if upgrade is None else 'Enabled' if upgrade else 'Disabled'})"
                        )
                        CONSOLE.info(
                            f"{'Status':<{col1}}: {dev.get('status_desc','Unknown'):<{col2}} (Status code: {str(dev.get('status','-'))})"
                        )
                        unit = dev.get("power_unit", "W")
                        CONSOLE.info(
                            f"{'AC Power':<{col1}}: {dev.get('generate_power',''):>3} {unit}"
                        )
                    else:
                        CONSOLE.warning(
                            "Neither Solarbank nor Inverter device, further details will be skipped"
                        )
                    CONSOLE.info("")
                    CONSOLE.debug(json.dumps(myapi.devices, indent=2))
                for sec in range(0, REFRESH):
                    now = datetime.now().astimezone()
                    if sys.stdin is sys.__stdin__:
                        print(  # noqa: T201
                            f"Site refresh: {int((next_refr-now).total_seconds()):>3} sec,  Device details refresh: {int((next_dev_refr-now).total_seconds()):>3} sec  (CTRL-C to abort)",
                            end="\r",
                            flush=True,
                        )
                    elif sec == 0:
                        # IDLE may be used and does not support cursor placement, skip time progress display
                        print(  # noqa: T201
                            f"Site refresh: {int((next_refr-now).total_seconds()):>3} sec,  Device details refresh: {int((next_dev_refr-now).total_seconds()):>3} sec  (CTRL-C to abort)",
                            end="",
                            flush=True,
                        )
                    time.sleep(1)
            return False

    except (ClientError, errors.AnkerSolixError) as err:
        CONSOLE.info("%s: %s", type(err), err)
        return False


# run async main
if __name__ == "__main__":
    try:
        if not asyncio.run(main()):
            CONSOLE.info("\nAborted!")
    except KeyboardInterrupt:
        CONSOLE.info("\nAborted!")
    except Exception as exception:
        CONSOLE.info("%s: %s", type(exception), exception)
