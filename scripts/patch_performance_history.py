import argparse
import json
import os
import sys
from glob import glob

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, "jobs_launcher")))
from core.countLostTests import PLATFORM_CONVERTATIONS

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--history_path",
                        required=True,
                        type=str,
                        metavar="<path>",
                        help="path to the folder with performance history files")
    parser.add_argument("--target_hash",
                        required=True,
                        type=str,
                        help="commit hash of the build that is a baseline")
    parser.add_argument("--scenarios",
                        required=True,
                        type=str,
                        help="comma-separated list of scenarios that should be patched or 'all' to update all scenarios")  # noqa: E501
    parser.add_argument("--platforms",
                        required=True,
                        type=str,
                        help="list of platforms scenarios of which should be updated. Example Windows:AMD_RX5700XT,AMD_RX6800XT;MacOS_ARM:AppleM2")  # noqa: E501
    parser.add_argument("--clear_history",
                        required=True,
                        type=str,
                        help="if 'True' the script clears history of results before the baseline build")

    args = parser.parse_args()

    # find the file that contains new baseline metrics
    history_files = glob(os.path.join(args.history_path, "*.json"))
    for history_file in history_files:
        with open(history_file) as file:
            content = json.load(file)

            if "general_info" in content and content["general_info"]["commit_sha"] == args.target_hash:
                baseline_history_file = history_file
                baseline_content = content
                break
    else:
        raise RuntimeError("File with metrics of the build with the target hash wasn't found")

    # mark results as baselines
    for platform in args.platforms.split(";"):
        raw_os_name = platform.split(":")[0]
        os_name = PLATFORM_CONVERTATIONS[raw_os_name]["os_name"]

        for raw_platform_name in platform.split(":")[1].split(","):
            platform_name = PLATFORM_CONVERTATIONS[raw_os_name]["cards"][raw_platform_name]
            formatted_platform_name = f"{platform_name} {os_name}"

            groups = baseline_content["data"][formatted_platform_name]["groups"]

            if args.scenarios == "all":
                for scenario in groups:
                    groups[scenario]["summary"]["baseline"] = True
            else:
                for scenario in args.scenarios.split(","):
                    if scenario in groups:
                        groups[scenario]["summary"]["baseline"] = True

    with open(baseline_history_file, "w") as file:
        json.dump(baseline_content, file, indent=4, sort_keys=True)

    if args.clear_history == "True":
        baseline_file_number = baseline_history_file.split("_")[-1]

        tracked_metrics_files = sorted(
            history_files,
            key=lambda x: int(os.path.splitext(x)[0].split("_")[-1])
        )

        for tracked_metrics_file in tracked_metrics_files:
            print(tracked_metrics_file)
            print(baseline_history_file)
            if tracked_metrics_file == baseline_history_file:
                break

            with open(tracked_metrics_file) as file:
                content = json.load(file)

                for platform in args.platforms.split(";"):
                    raw_os_name = platform.split(":")[0]
                    os_name = PLATFORM_CONVERTATIONS[raw_os_name]["os_name"]

                    for raw_platform_name in platform.split(":")[1].split(","):
                        platform_name = PLATFORM_CONVERTATIONS[raw_os_name]["cards"][raw_platform_name]
                        formatted_platform_name = f"{platform_name} {os_name}"

                        groups = baseline_content["data"][formatted_platform_name]["groups"]

                        if args.scenarios == "all":
                            if formatted_platform_name in content["data"]:
                                del content["data"][formatted_platform_name]
                        else:
                            for scenario in args.scenarios.split(","):
                                if scenario in groups:
                                    del groups[scenario]

            with open(tracked_metrics_file, "w") as file:
                json.dump(content, file, indent=4, sort_keys=True)
