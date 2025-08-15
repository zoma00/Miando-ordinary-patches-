#!/bin/bash
cd /home/hazem/Miando/patterns/json_split
python3 pattern_json_live.py >> /var/log/pattern_json_live.log 2>&1
