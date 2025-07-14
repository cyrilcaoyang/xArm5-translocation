# Key Features

The `xArm-translocation` controller provides a robust, feature-rich interface for controlling UFACTORY xArm robots, with a strong emphasis on safety, reliability, and ease of use. It supports multiple robot models, grippers, and a linear track, all managed through a single, unified API.

The system is designed to operate in three distinct stages, from pure software simulation to real hardware, ensuring code can be developed and tested safely and efficiently.

---

## Core Features

| Feature                 | Description                                                                                                                              |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **Multi-Model Support** | Natively supports **xArm5, xArm6, xArm7, and the 850 model**. The controller automatically adjusts joint limits and behavior.                |
| **Unified API**         | A single, consistent set of methods (`move_to_position`, `open_gripper`, etc.) control the arm, gripper, and linear track.                  |
| **Component System**    | The arm, gripper, and track are treated as components that can be enabled, disabled, and monitored independently (`enable_gripper_component`). |
| **Flexible Config**     | All settings are managed through clear `.yaml` files (`xarm_config.yaml`, `safety.yaml`, etc.), separating configuration from code.        |
| **Named Locations**     | Pre-define and move to named locations (e.g., "home", "pickup_station") stored in `location_config.yaml` for repeatable operations.        |

---

## Simulation & Testing

The controller offers two distinct simulation modes, allowing for a comprehensive, three-stage testing workflow that moves from logic validation to full-physics simulation before deploying to hardware.

| Simulation Mode           | Description                                                                                                                                    |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Software Simulation**  | A lightweight, built-in mode (`simulation_mode=True`) that requires no external software. Ideal for fast development cycles and CI/CD.         |
| **2. Docker Simulation**    | Uses the official UFACTORY simulator for high-fidelity physics, realistic dynamics, and precise, mesh-based collision detection.                   |

*For a detailed guide, see the [**Testing Guide**](./TESTING.md).*

---

## Safety & Error Handling

Safety is a primary design principle, with multiple layers of validation and intelligent error recovery.

| Safety Feature                  | Description                                                                                                                                                       |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Multi-Level Safety**          | Configure the `safety_level` (Strict, Medium, Loose) to automatically adjust speed, acceleration, and validation strictness.                                      |
| **Built-in Collision Checking** | All movement methods (`move_to_position`, `move_joints`) automatically perform collision checks against joint limits and workspace boundaries.                      |
| **Configurable Safety Zones**   | Define custom "keep-out" zones in `safety.yaml` to prevent the robot from entering restricted areas.                                                               |
| **Intelligent Error Recovery**  | The controller can automatically attempt to recover from common, non-critical errors. State and error history are tracked for diagnostics.                            |
| **Emergency Stop**              | A universal `stop_motion()` method provides an immediate halt for all robot, gripper, and track movements.                                                            |

---

## Gripper & Linear Track

| Component Feature         | Description                                                                                                                                                            |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Universal Gripper API** | `open_gripper()` and `close_gripper()` work seamlessly with any configured gripper type (**Bio Gripper, Standard Gripper, or Robotiq**).                                   |
| **Linear Track Control**  | If `enable_track=True`, the controller provides validated motion control for the linear track, including position and speed limits defined in `linear_track_config.yaml`. |

---

## Monitoring & Performance

The controller includes systems for monitoring the robot's health and performance in real-time when connected to physical hardware.

| Monitoring Feature           | Description                                                                                                                                 |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **Performance Tracking**     | Automatically logs key metrics like cycle times and command success rates, helping to diagnose bottlenecks and optimize robot programs.           |
| **Predictive Maintenance**   | Monitors joint temperatures and torque (if available) to provide early warnings for potential hardware issues.                                |
| **Real-time State Callbacks**| Register custom callback functions to react to events like state changes or errors, enabling more dynamic and responsive applications.          | 