#!/home/r09491/anker-solix-api-2/.venv/bin/python3

import logging
import os
import sys

from datetime import datetime

import asyncio
from aiohttp import ClientSession

from anker_solix_api import api, errors, common
from anker_solix_api.types import SolarbankTimeslot

_LOGGER: logging.Logger = logging.getLogger(__name__)
_LOGGER.addHandler(logging.StreamHandler(sys.stdout))

async def main() -> None:
    """Create the aiohttp session and run the example."""
    print("Testing Solix API:")
    try:
        async with ClientSession() as websession:
            myapi = api.AnkerSolixApi("r09491@gmail.com","copteR_1954","de",websession, _LOGGER)

            deviceSn = "AZV6Y60D33200788"
            siteId = "26e56751-fe51-40a6-8fb0-b9ce5d6c8700"

            await myapi.set_home_load(
                siteId=siteId,
                deviceSn=deviceSn,
                preset=None,
                dev_preset=None,
                all_day=None,
                export=None,
                charge_prio=None,
                insert_slot=SolarbankTimeslot(
                    start_time=datetime.strptime("00:00", "%H:%M"),
                    end_time=datetime.strptime("23:59", "%H:%M"),
                    appliance_load=250,
                    device_load=None,
                    allow_export=None,
                    charge_priority_limit=None,
                ),
            )
        
            # print schedule table from requeried and updated schedule object in the device cache
            common.print_schedule((myapi.devices.get(deviceSn) or {}).get("schedule"))

    except Exception as err:
        print(f"{type(err)}: {err}")

asyncio.run(main())        
   
