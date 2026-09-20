# SiteCare Setup Instructions

**GitHub Link:** [https://github.com/ShabbirMahmood/SiteCare_Prototype](https://github.com/ShabbirMahmood/SiteCare_Prototype)

## 1. Open the Project in VS Code

Download/extract the repository or clone it. In VS Code, choose **File → Open Folder** and select the folder containing `run.py`.

Open **Terminal → New Terminal**. From the terminal dropdown, choose **Select Default Profile → Command Prompt**, then open a new terminal. The commands below are for Windows **CMD**.

## 2. Check Python

```bat
python --version
py -0p
```

Python 3.13 is recommended; the launcher requires 3.11 or newer. Install Python 3.13 if `py -0p` does not list it. This workspace currently uses Python 3.12.10 and has also passed the project tests on that environment; `py -3.12` can be used below when maintaining that setup.

## 3. Create and Activate the Environment

For first-time setup:

```bat
py -3.13 -m venv .venv
.venv\Scripts\activate
```

Skip environment creation if a working `.venv` already exists. The terminal should show `(.venv)`. If using the VS Code Python extension, select `.venv\Scripts\python.exe` with **Python: Select Interpreter**.

## 4. Install Libraries and Run

```bat
python.exe -m pip install -r requirements.txt
python.exe run.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000/). Keep the server terminal open. Do not use VS Code Live Server or open `index.html` directly.

For later runs, only activation and startup are needed:

```bat
.venv\Scripts\activate
python.exe run.py
```

## 5. User Details

A fresh installation has **no built-in accounts**. Create the administrator on the first screen. Then use **Settings & Data → Add User** to create a nurse account.

These are the requested **demo account examples** for a new installation:

| Role | Username | Display Name | Example Password |
| --- | --- | --- | --- |
| Administrator | `Admin` | Admin | `adminadminadmin` |
| Nurse | `Nurse A` | Nurse A | `nursenursenurse` |

**Existing workspace:** the administrator's actual login username is `adminadminadmin`, its display name is **Admin**, and the supplied administrator password matches. `Nurse A` exists, but its current password differs from the example above. Use the reset command below if you want to set that demo password. These instructions do not create accounts or change passwords automatically.

Usernames are case-sensitive; spaces matter. Use passwords of 12–128 characters. The printed examples are for a disposable demonstration setup.

## 6. Stop the Server

1. Save your work.
2. Open the VS Code terminal panel with **View → Terminal** and select the existing terminal running SiteCare from the terminal list.
3. Click inside that server terminal and press **Ctrl+C**. Wait until the command prompt returns.
4. Optionally leave the virtual environment:

```bat
deactivate
```

Closing a browser or hiding the terminal panel does not stop the server. `deactivate` alone does not stop a running server.

## 7. Lost Terminal or Port 8000 Already in Use

Open a new CMD terminal in the project folder and activate `.venv`. A port is released by stopping the process listening on it.

**Find the listener.** This Python command calls Windows `netstat`; the last column is the process ID (PID):

```bat
python.exe -c "import subprocess; rows=subprocess.check_output(['netstat','-ano','-p','tcp'],text=True).splitlines(); print('\n'.join(r for r in rows if len(r.split())==5 and r.split()[1].rsplit(':',1)[-1]=='8000' and r.split()[3]=='LISTENING') or 'Port 8000 is free.')"
```

**Identify it.** Replace `12345` with that PID. This Python command asks Windows PowerShell for the process details:

```bat
python.exe -c "import subprocess; subprocess.run(['powershell.exe','-NoProfile','-Command','Get-CimInstance Win32_Process | Where-Object ProcessId -eq 12345 | Format-List ProcessId,ExecutablePath,CommandLine'],check=True)"
```

Confirm that it is your SiteCare `run.py` process. Prefer **Ctrl+C** if its terminal is still available. Otherwise, replace `12345` below with the confirmed PID and force-stop that process; unsaved work can be lost:

```bat
python.exe -c "import subprocess; subprocess.run(['taskkill','/PID','12345','/F'],check=True)"
```

Run the listener check again, then start SiteCare once:

```bat
python.exe run.py
```

If port 8000 belongs to another application, leave it running and choose another port:

```bat
python.exe run.py --port 8001
```

Then open [http://127.0.0.1:8001](http://127.0.0.1:8001/). No additional Python package is needed for these port commands.

## 8. Reset Passwords

Stop SiteCare first. Reset **one account per command**, using its exact login username. The command asks privately for a new password twice and revokes that account's existing sessions.

For this workspace's existing accounts:

```bat
.venv\Scripts\python.exe manage.py reset-password adminadminadmin
.venv\Scripts\python.exe manage.py reset-password "Nurse A"
```

For a fresh installation where you created the username `Admin`, use:

```bat
.venv\Scripts\python.exe manage.py reset-password Admin
```

There is no single **Reset All Passwords** command. Repeat the command for each account, then restart SiteCare.

## 9. Backup and Maintenance

```bat
.venv\Scripts\python.exe manage.py backup
.venv\Scripts\python.exe manage.py check
```

Backups go to `backups/`. Records and photographs are in `data/`; retain that folder when updating the source. If the server uses `--data-dir`, supply the same directory to maintenance commands.

After backend changes, restart the server; after interface changes, refresh with **Ctrl+F5**. See [User Manual](user_manual.md) and [Technical Architecture](technical_architecture.md) for operation and implementation details.
