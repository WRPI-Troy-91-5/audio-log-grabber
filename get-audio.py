#######################################################################################
# get-audio.py                                                                        #
# -------------                                                                       #
# Script to get the a specified range of logs in a single file                        #
#                                                                                     #
# IMPORTANT NOTE                                                                      #
# ---------------                                                                     #
# THIS SCRIPT IS NOT PORTABLE AND IS HARDCODED TO MATCH THIS FILESYSTEM STRUCTURE.    #
# IF YOU ATTEMPT TO USE THIS ON YOUR OWN MACHINE, YOU MUST CHANGE THE FOLDER LOCATION #
# IN EITHER YOUR SYSTEM OR THE CODE.                                                  #
#                                                                                     #
#######################################################################################

import sys
import os
from datetime import datetime, timedelta

def get_input(prompt, length):
    while True:
        inpt = input(prompt)
        if (inpt == "-1"):
            exit()
        if (len(inpt) == length):
            return inpt

def get_bound():
    try:
        bound = [int(get_input("  Year [xxxx]: ", 4)),
                 int(get_input("  Month [xx]: ", 2)),
                 int(get_input("  Day [xx]: ", 2)),
                 int(get_input("  Hour (24h format) [xx]: ", 2)),
                 int(get_input("  Minute [xx]: ", 2)),
                 int(get_input("  Second [xx]: ", 2))]
        return datetime(bound[0], bound[1], bound[2], bound[3], bound[4], bound[5])
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def get_bounds():
    # Range lower bound
    print("Enter the starting time (-1 to exit): ")
    begin = get_bound()

    # Range upper bound
    print("Enter the ending time (-1 to exit): ")
    end = get_bound()

    # Confirm bounds
    print(f"Bounds are: \nBegin: {begin}")
    print(f"End: {end}")

    while True:
        confirm = input("Continue? [Y/n]: ")
        if (confirm in ["N", "n"]): sys.exit(0)
        if (confirm in ["Y", "y", ""]): break

    return (begin, end)

def strtodate(string):
    date = None
    try:
        date = datetime.strptime(string, "%Y_%m_%d_%H_%M_%S")
    except:
        try:
            date = datetime.strptime(string, "%Y_%m_%d_%H_%M")
        except:
            date = datetime.strptime(string, "%Y_%m_%d_%I_%M_%p")
    return date

def datetostr(date):
    return datetime.strftime(date, "%Y-%m-%d-%H-%M-%S")

def get_audio_logs(bounds):
    # Get the logs
    logs = os.listdir("/local-zfs/audio-log")
    logs_copy = [] # List to contain the filtered logs
    for i in range(len(logs)):
        # Filter for only mp3 files
        if (logs[i][-4:] != ".mp3"):
            continue

        # Get date from filename (excluding the 3char file extension)
        date = strtodate(logs[i][:-4])

        # skip logs that are not within the bounds and given a 30 minute beginning (1800 second) window 
        # Filter the lower bound
        if (date < bounds[0] and abs((date-bounds[0]).total_seconds()) >= 1800):                                                                     
            continue

        # Filter the upper bound, any log exceeding this will be out of bounds
        if (date > bounds[1]):
            continue

        # Add the logs that make it past the filter
        logs_copy.append(logs[i])

    # Sort the unfiltered list
    logs_copy.sort()
    return logs_copy

if __name__ == "__main__":
    print("NOTE")
    print("-----")
    print("Logs before 10/30/2025 @ 0330 cannot be combined with any that come after it")
    print("")

    # Get the date+time bounds to filter out the total logs by    
    bounds = get_bounds()

    # Get the logs that match the bounds filter
    audio_logs = get_audio_logs(bounds)

    # Copy the logs to the temp folder
    os.system(f"cd /local-zfs/audio-log && cp -v {' '.join(audio_logs)} /local-zfs/get-audio-temp/")

    # If there are two or more clips the bounding clips will have to be cut/adjusted and recombined
    if (len(audio_logs) >= 2):
        # Find how many seconds into the first clip and from the end of the last clip need to be cut out
        begin_cut_time = int(abs((bounds[0]-strtodate(audio_logs[0][:-4])).total_seconds()))
        end_cut_time = int(abs((bounds[1]-strtodate(audio_logs[-1][:-4])).total_seconds()))
        # The above time is just how much needs to be removed
        # Need to calculate the total time of the new clip for processing

        # Need to define a list to store the lost files caused by these operations
        saved_logs = []
        # Cut the beginning segment of the first log if needed
        if (begin_cut_time != 0):
            os.system(f"cd /local-zfs/get-audio-temp && ffmpeg -ss {begin_cut_time} -i {audio_logs[0]} new_temp_start.mp3")
            saved_logs.append(audio_logs[0])
            audio_logs[0] = "new_temp_start.mp3"
    
        # Cut the end segment of the last log if needed
        if (end_cut_time != 0):
            os.system(f"cd /local-zfs/get-audio-temp && ffmpeg -t {end_cut_time} -i {audio_logs[-1]} new_temp_end.mp3")
            saved_logs.append(audio_logs[-1])
            audio_logs[-1] = "new_temp_end.mp3"

        # Combine the logs into a single file
        os.system(f"cd /local-zfs/get-audio-temp && ffmpeg -i 'concat:{'|'.join(audio_logs)}' -acodec copy ./{datetostr(bounds[0])}-{datetostr(bounds[1])}.mp3")    

        # Prompt the user with the new file location
        print(f"Output file location: /local-zfs/get-audio-temp/{datetostr(bounds[0])}-{datetostr(bounds[1])}.mp3")

        # Remove the temp audio logs
        os.system(f"cd /local-zfs/get-audio-temp && rm -v {' '.join(audio_logs)} {' '.join(saved_logs)}")

    # Case of a single log
    elif (len(audio_logs) == 1):
        # Find how many seconds to skip into and cut from the end of the single log
        begin_cut_time = int(abs(strtodate(audio_logs[0][:-4])-bounds[0]).total_seconds())
        end_cut_time = int(abs((bounds[1]-strtodate(audio_logs[0][:-4])).total_seconds()))
        # Total segment = end bound - begin bound
        total_time_segment = int((bounds[1] - bounds[0]).total_seconds())

        # Use ffmpeg to seek into and cut from the end
        os.system(f"cd /local-zfs/get-audio-temp && ffmpeg -ss {begin_cut_time} -t {total_time_segment} -i {audio_logs[0]} ./{datetostr(bounds[0])}-{datetostr(bounds[1])}.mp3")

        # Prompt the user for the location
        print(f"Output file location: /local-zfs/get-audio-temp/{datetostr(bounds[0])}-{datetostr(bounds[1])}.mp3")

    else:
        print("No logs match your bound criteria")
