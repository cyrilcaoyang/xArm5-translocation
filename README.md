# PyxArm
Python code to drive the movement of xArm and linear rail from UFactory to manipulate objects.


## Installation

### With a real robot

Please install SDK first in your environment from the [xArm-Python-SDK](https://github.com/xArm-Developer/xArm-Python-SDK) repository.

  1. `git clone https://github.com/xArm-Developer/xArm-Python-SDK.git`
  2. `cd xArm-Python-SDK`
  3. `python setup.py install`

### With the simulator (no robot required)

It's possible to use a simulator to run the UFACTORY Studio UI and use Blockly without being connected to a physical xArm. This is based on a docker image.

Reference: [UFACTORY Studio simulation](https://forum.ufactory.cc/t/ufactory-studio-simulation/3719)

#### 1. Pull the docker image

```bash
docker pull danielwang123321/uf-ubuntu-docker
```

#### 2. Create and run the container

The following command includes web simulation and SDK ports.

```bash
docker run -it --name uf_software -p 18333:18333 -p 502:502 -p 503:503 -p 504:504 -p 30000:30000 -p 30001:30001 -p 30002:30002 -p 30003:30003 danielwang123321/uf-ubuntu-docker
```

#### 3. Run the xArm robot firmware and UFACTORY Studio

For example, to start the UFACTORY Studio and firmware of xArm 6, run the following inside the container.

```bash
/xarm_scripts/xarm_start.sh 6 6
```

The arguments `6 6` correspond to xArm 6. Change it according to your robot:
*   `5 5`: xArm 5
*   `6 6`: xArm 6
*   `7 7`: xArm 7
*   `6 9`: Lite 6
*   `6 12`: 850

#### 4. Access the UFACTORY Studio web simulation

Open a web browser and go to `http://127.0.0.1:18333` or `http://localhost:18333`.

If a prompt "Unable to get robot SN…" appears, click "Close" to proceed.

#### 5. Connect to the simulator from your code

To connect to the simulated robot from your Python code, use the IP address `127.0.0.1`.

If you are running code generated from "Blockly-to-Python", you may need to add `check_joint_limit=False` when creating the `XArmAPI` instance.

```python
arm = XArmAPI('127.0.0.1', baud_checkset=False, check_joint_limit=False)
```
