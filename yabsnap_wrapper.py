import subprocess
import json
import argparse
from datetime import datetime
import npyscreen

def get_snapshots():
    try:
        result = subprocess.run(['yabsnap', 'list-json'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            npyscreen.notify_confirm("Error retrieving snapshot list:\n" + result.stderr, title="Error")
            return []
        snapshots = [json.loads(line) for line in result.stdout.splitlines()]
        return snapshots
    except Exception as e:
        npyscreen.notify_confirm(f"An error occurred: {e}", title="Error")
        return []

def format_timestamp(timestamp):
    dt = datetime.strptime(timestamp, '%Y%m%d%H%M%S')
    return dt.strftime('%d.%m.%y %H:%M')

def generate_rollback_script(timestamp):
    try:
        result = subprocess.run(['yabsnap', 'rollback-gen', timestamp], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            npyscreen.notify_confirm("Error generating rollback script:\n" + result.stderr, title="Error")
            return None
        return result.stdout
    except Exception as e:
        npyscreen.notify_confirm(f"An error occurred: {e}", title="Error")
        return None

def save_script_to_file(script, filename):
    try:
        with open(filename, 'w') as file:
            file.write(script)
        npyscreen.notify_confirm(f"Script saved successfully to {filename}", title="Success")
    except Exception as e:
        npyscreen.notify_confirm(f"An error occurred while saving the file: {e}", title="Error")

def execute_script(filename):
    try:
        subprocess.run(['bash', filename], check=True)
        npyscreen.notify_confirm(f"Script {filename} executed successfully.", title="Success")
    except subprocess.CalledProcessError as e:
        npyscreen.notify_confirm(f"An error occurred during script execution: {e}", title="Error")

class SnapshotSelectorApp(npyscreen.NPSAppManaged):
    def __init__(self, args):
        self.args = args
        self.snapshots = get_snapshots()
        super().__init__()

    def onStart(self):
        if not self.snapshots:
            npyscreen.notify_confirm("No snapshots available for rollback.", title="Info")
            self.setNextForm(None)
            return
        self.addForm("MAIN", SnapshotSelectorForm, name="Snapshot Selector")

class SnapshotSelectorForm(npyscreen.ActionForm):
    def create(self):
        self.snapshots = self.parentApp.snapshots
        self.unique_snapshots = {snapshot['file']['timestamp']: snapshot for snapshot in self.snapshots}
        self.timestamp_list = list(self.unique_snapshots.keys())

        self.snapshot_list = self.add(npyscreen.TitleSelectOne, max_height=len(self.timestamp_list) + 2, value=[0], name="Snapshots", scroll_exit=True)
        self.update_snapshot_list()

    def update_snapshot_list(self):
        formatted_snapshots = []
        for timestamp in self.timestamp_list:
            snapshot = self.unique_snapshots[timestamp]
            readable_time = format_timestamp(timestamp)
            comment = snapshot['comment']
            source = snapshot['source']
            formatted_snapshots.append(f"{readable_time} - {comment} (source: {source})")
        self.snapshot_list.values = formatted_snapshots
        self.snapshot_list.display()

    def on_ok(self):
        selected_index = self.snapshot_list.value[0]
        selected_timestamp = self.timestamp_list[selected_index]
        rollback_script = generate_rollback_script(selected_timestamp)
        if rollback_script:
            save_script_to_file(rollback_script, self.parentApp.args.output)
            if npyscreen.notify_yes_no("Do you want to execute the rollback script now?", title="Execute Script"):
                execute_script(self.parentApp.args.output)
        self.parentApp.setNextForm(None)

    def on_cancel(self):
        self.parentApp.setNextForm(None)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Yabsnap rollback script generator.")
    parser.add_argument('-o', '--output', type=str, default='rollback.sh', help='Output file for the rollback script')
    args = parser.parse_args()
    
    app = SnapshotSelectorApp(args)
    app.run()
