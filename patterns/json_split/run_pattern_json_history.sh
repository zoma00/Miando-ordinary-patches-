#!/bin/bash
cd /home/hazem/Miando/patterns/json_split
python3 pattern_json_history.py >> /var/log/pattern_json_history.log 2>&1
