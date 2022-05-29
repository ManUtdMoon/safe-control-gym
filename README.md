# Safe-control-gym

## Overview
Note that this version is revision of the [original repository](https://github.com/utiasDSL/safe-control-gym) and we focus on the circle tracking task of a **2D** quadrotor in the $xz$-plane.

Major differences include:
- Adding new environment configurations `examples/constrained_tracking_eval.yaml` and `examples/constrained_tracking.yaml` about the initial position/velocity of the 2D quadrotor;
- `norm_act_scale=1.0` in `safe_control_gym/envs/gym_pybullet_drones/quadrotor.py` because the the original value `0.1` may lead to a limited control over the quadrotor and less violation. Therefore, `1.0` is **harder** and **more capable**;
- Adding info about the tracking error of angular speed in the `info` variable;
- The coefficients of different error in the reward function are modified but not essential.

## Installation of safe-control-gym
```
$ sudo apt-get install libgmp-dev                                  # Install a necessary lib
$ cd /your/path/to/safe-control-gym/
$ pip install -e .                                                 # Install the repository
```


## Please cite the original authors' paper:
```
@article{brunke2021safe,
         title={Safe Learning in Robotics: From Learning-Based Control to Safe Reinforcement Learning}, 
         author={Lukas Brunke and Melissa Greeff and Adam W. Hall and Zhaocong Yuan and Siqi Zhou and Jacopo Panerati and Angela P. Schoellig},
         journal = {Annual Review of Control, Robotics, and Autonomous Systems},
         year={2021},
         url = {https://arxiv.org/abs/2108.06266}}
```