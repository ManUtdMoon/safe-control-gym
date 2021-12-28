"""A quadrotor trajectory tracking example.

Notes:
    Includes and uses PID control.

Run as:

    $ python3 tracking.py --overrides ./tracking.yaml

"""
import time
import math
import numpy as np
import pybullet as p
import casadi as cs
from scipy.spatial.transform import Rotation

from safe_control_gym.utils.utils import str2bool
from safe_control_gym.utils.configuration import ConfigFactory
from safe_control_gym.utils.registration import make


def main():
    """The main function creating, running, and closing an environment.

    """

    # Create an environment
    CONFIG_FACTORY = ConfigFactory()               
    config = CONFIG_FACTORY.merge()
    # Set iterations and episode counter.
    num_episodes = 1
    ITERATIONS = int(config.quadrotor_config['episode_len_sec']*config.quadrotor_config['ctrl_freq'])
    for i in range(num_episodes):
        # Start a timer.
        START = time.time()
        # if i == 1:
        #     config.quadrotor_config['task_info']['trajectory_type'] = 'circle'
        # elif i == 2:
        #     config.quadrotor_config['task_info']['trajectory_type'] = 'square'
        env = make('quadrotor', **config.quadrotor_config)
        # Create controller.
        action = np.zeros(2)
        ctrl = DSLPIDControl()
        # Reset the environment, obtain and print the initial observations.
        initial_obs, initial_info = env.reset()
        # Plot trajectory.
        for i in range(0, initial_info['x_reference'].shape[0], 10):
            p.addUserDebugLine(lineFromXYZ=[initial_info['x_reference'][i-10,0], 0, initial_info['x_reference'][i-10,2]],
                               lineToXYZ=[initial_info['x_reference'][i,0], 0, initial_info['x_reference'][i,2]],
                               lineColorRGB=[1, 0, 0],
                               # lifeTime=2 * env._CTRL_TIMESTEP,
                               physicsClientId=env.PYB_CLIENT)
        position_list = []
        rew_list = []
        ref_list = []
        position_list.append((initial_obs[0], initial_obs[2]))
        ref_list.append((initial_info['x_reference'][(env.start_index) % (env.X_GOAL.shape[0]), 0],
                        initial_info['x_reference'][(env.start_index) % (env.X_GOAL.shape[0]), 2])
                        )

        info_dict_of_list = {}
        print(initial_obs[0], initial_obs[2])

        # Run the experiment.
        for i in range(ITERATIONS):
            # Step the environment and print all returned information.
            obs, reward, done, info = env.step(action)
            # Print the last action and the information returned at each step.
            print(i, '-th step.')
            position_list.append((obs[0], obs[2]))
            print(action, '\n', obs, '\n', reward, '\n', done, '\n', info, '\n')
            # Compute the next action.
            action, _, _ = ctrl.computeControl(control_timestep=env.CTRL_TIMESTEP,
                                               cur_pos=np.array([obs[0], 0, obs[2]]),
                                               cur_quat=np.array(p.getQuaternionFromEuler([0,
                                                                                           obs[4],
                                                                                           0
                                                                                           ])),
                                               cur_vel=np.array([obs[1], 0, obs[3]]),
                                               cur_ang_vel=np.array([0, obs[4], 0]),
                                               target_pos=np.array([
                                                                    initial_info['x_reference'][(i+env.start_index)%(env.X_GOAL.shape[0]),0],
                                                                    0,
                                                                    initial_info['x_reference'][(i+env.start_index)%(env.X_GOAL.shape[0]),2]
                                                                    ]),
                                               target_vel=np.array([
                                                                    initial_info['x_reference'][(i+env.start_index)%(env.X_GOAL.shape[0]),1],
                                                                    0,
                                                                    initial_info['x_reference'][(i+env.start_index)%(env.X_GOAL.shape[0]),3]
                                                                    ])
                                               )
            action = ctrl.KF * action**2
            action = np.array([action[0]+action[3], action[1]+action[2]])
            action = PIDcontrol2normalized(action, env)
            rew_list.append(reward)
            ref_list.append((initial_info['x_reference'][(i+env.start_index) % (env.X_GOAL.shape[0]), 0],
                             initial_info['x_reference'][(i+env.start_index) % (env.X_GOAL.shape[0]), 2],))
            if i == 0:
                for key in info.keys():
                    info_dict_of_list[key] = [info[key]]
            else:
                for key in info_dict_of_list.keys():
                    info_dict_of_list[key].append(info[key])        

            # env.render()
            if done:
                _, _ = env.reset()
        # Close the environment and print timing statistics.
        env.close()
        for key in info_dict_of_list.keys():
            tmp_list = info_dict_of_list[key]
            print('avg_' + key, sum(tmp_list)/len(tmp_list), '\n')
        print('return', sum(rew_list))
        elapsed_sec = time.time() - START
        print("\n{:d} iterations (@{:d}Hz) and {:d} episodes in {:.2f} seconds, i.e. {:.2f} steps/sec for a {:.2f}x speedup.\n"
              .format(ITERATIONS, env.CTRL_FREQ, num_episodes, elapsed_sec, ITERATIONS/elapsed_sec, (ITERATIONS*env.CTRL_TIMESTEP)/elapsed_sec))

        # np.save('./PID_traj.npy', np.array(position_list))
        # np.save('./PID_ref.npy', np.array(ref_list))


class DSLPIDControl():
    """PID control class for Crazyflies.

    Based on work conducted at UTIAS' DSL by SiQi Zhou and James Xu.

    """

    def __init__(self,
                 g: float=9.8
                 ):
        """Common control classes __init__ method.

        Args
            g (float, optional): The gravitational acceleration in m/s^2.

        """
        self.GRAVITY = 9.8 * 0.027
        self.KF = 3.16e-10
        self.KM = 7.94e-12
        self.P_COEFF_FOR = np.array([.4, .4, 1.25])
        self.I_COEFF_FOR = np.array([.05, .05, .05])
        self.D_COEFF_FOR = np.array([.2, .2, .5])
        self.P_COEFF_TOR = np.array([70000., 70000., 60000.])
        self.I_COEFF_TOR = np.array([.0, .0, 500.])
        self.D_COEFF_TOR = np.array([20000., 20000., 12000.])
        self.PWM2RPM_SCALE = 0.2685
        self.PWM2RPM_CONST = 4070.3
        self.MIN_PWM = 20000
        self.MAX_PWM = 65535
        self.MIXER_MATRIX = np.array([ [.5, -.5,  -1], [.5, .5, 1], [-.5,  .5,  -1], [-.5, -.5, 1] ])
        self.reset()

    def reset(self):
        """Resets the control classes.

        The previous step's and integral errors for both position and attitude are set to zero.

        """
        self.control_counter = 0
        # Store the last roll, pitch, and yaw.
        self.last_rpy = np.zeros(3)
        # Initialized PID control variables.
        self.last_pos_e = np.zeros(3)
        self.integral_pos_e = np.zeros(3)
        self.last_rpy_e = np.zeros(3)
        self.integral_rpy_e = np.zeros(3)
    
    def computeControl(self,
                       control_timestep,
                       cur_pos,
                       cur_quat,
                       cur_vel,
                       cur_ang_vel,
                       target_pos,
                       target_rpy=np.zeros(3),
                       target_vel=np.zeros(3),
                       target_rpy_rates=np.zeros(3)
                       ):
        """Computes the PID control action (as RPMs) for a single drone.

        This methods sequentially calls `_dslPIDPositionControl()` and `_dslPIDAttitudeControl()`.
        Parameter `cur_ang_vel` is unused.

        Args:
            control_timestep (float): The time step at which control is computed.
            cur_pos (ndarray): (3,1)-shaped array of floats containing the current position.
            cur_quat (ndarray): (4,1)-shaped array of floats containing the current orientation as a quaternion.
            cur_vel (ndarray): (3,1)-shaped array of floats containing the current velocity.
            cur_ang_vel (ndarray): (3,1)-shaped array of floats containing the current angular velocity.
            target_pos (ndarray): (3,1)-shaped array of floats containing the desired position.
            target_rpy (ndarray, optional): (3,1)-shaped array of floats containing the desired orientation as roll, pitch, yaw.
            target_vel (ndarray, optional): (3,1)-shaped array of floats containing the desired velocity.
            target_rpy_rates (ndarray, optional): (3,1)-shaped array of floats containing the desired roll, pitch, and yaw rates.

        Returns:
            ndarray: (4,1)-shaped array of integers containing the RPMs to apply to each of the 4 motors.
            ndarray: (3,1)-shaped array of floats containing the current XYZ position error.
            float: The current yaw error.

        """
        self.control_counter += 1
        thrust, computed_target_rpy, pos_e = self._dslPIDPositionControl(control_timestep,
                                                                         cur_pos,
                                                                         cur_quat,
                                                                         cur_vel,
                                                                         target_pos,
                                                                         target_rpy,
                                                                         target_vel
                                                                         )
        rpm = self._dslPIDAttitudeControl(control_timestep,
                                          thrust,
                                          cur_quat,
                                          computed_target_rpy,
                                          target_rpy_rates
                                          )
        cur_rpy = p.getEulerFromQuaternion(cur_quat)
        return rpm, pos_e, computed_target_rpy[2] - cur_rpy[2]
    
    def _dslPIDPositionControl(self,
                               control_timestep,
                               cur_pos,
                               cur_quat,
                               cur_vel,
                               target_pos,
                               target_rpy,
                               target_vel
                               ):
        """DSL's CF2.x PID position control.

        Args:
            control_timestep (float): The time step at which control is computed.
            cur_pos (ndarray): (3,1)-shaped array of floats containing the current position.
            cur_quat (ndarray): (4,1)-shaped array of floats containing the current orientation as a quaternion.
            cur_vel (ndarray): (3,1)-shaped array of floats containing the current velocity.
            target_pos (ndarray): (3,1)-shaped array of floats containing the desired position.
            target_rpy (ndarray): (3,1)-shaped array of floats containing the desired orientation as roll, pitch, yaw.
            target_vel (ndarray): (3,1)-shaped array of floats containing the desired velocity.

        Returns:
            float: The target thrust along the drone z-axis.
            ndarray: (3,1)-shaped array of floats containing the target roll, pitch, and yaw.
            float: The current position error.

        """
        cur_rotation = np.array(p.getMatrixFromQuaternion(cur_quat)).reshape(3, 3)
        pos_e = target_pos - cur_pos
        vel_e = target_vel - cur_vel
        self.integral_pos_e = self.integral_pos_e + pos_e*control_timestep
        self.integral_pos_e = np.clip(self.integral_pos_e, -2., 2.)
        self.integral_pos_e[2] = np.clip(self.integral_pos_e[2], -0.15, .15)
        # PID target thrust.
        target_thrust = np.multiply(self.P_COEFF_FOR, pos_e) \
                        + np.multiply(self.I_COEFF_FOR, self.integral_pos_e) \
                        + np.multiply(self.D_COEFF_FOR, vel_e) + np.array([0, 0, self.GRAVITY])
        scalar_thrust = max(0., np.dot(target_thrust, cur_rotation[:,2]))
        thrust = (math.sqrt(scalar_thrust / (4*self.KF)) - self.PWM2RPM_CONST) / self.PWM2RPM_SCALE
        target_z_ax = target_thrust / np.linalg.norm(target_thrust)
        target_x_c = np.array([math.cos(target_rpy[2]), math.sin(target_rpy[2]), 0])
        target_y_ax = np.cross(target_z_ax, target_x_c) / np.linalg.norm(np.cross(target_z_ax, target_x_c))
        target_x_ax = np.cross(target_y_ax, target_z_ax)
        target_rotation = (np.vstack([target_x_ax, target_y_ax, target_z_ax])).transpose()
        # Target rotation.
        target_euler = (Rotation.from_matrix(target_rotation)).as_euler('XYZ', degrees=False)
        if np.any(np.abs(target_euler) > math.pi):
            print("\n[ERROR] ctrl it", self.control_counter, "in Control._dslPIDPositionControl(), values outside range [-pi,pi]")
        return thrust, target_euler, pos_e
    
    def _dslPIDAttitudeControl(self,
                               control_timestep,
                               thrust,
                               cur_quat,
                               target_euler,
                               target_rpy_rates
                               ):
        """DSL's CF2.x PID attitude control.

        Args:
            control_timestep (float): The time step at which control is computed.
            thrust (float): The target thrust along the drone z-axis.
            cur_quat (ndarray): (4,1)-shaped array of floats containing the current orientation as a quaternion.
            target_euler (ndarray): (3,1)-shaped array of floats containing the computed target Euler angles.
            target_rpy_rates (ndarray): (3,1)-shaped array of floats containing the desired roll, pitch, and yaw rates.

        Returns:
            ndarray: (4,1)-shaped array of integers containing the RPMs to apply to each of the 4 motors.

        """
        cur_rotation = np.array(p.getMatrixFromQuaternion(cur_quat)).reshape(3, 3)
        cur_rpy = np.array(p.getEulerFromQuaternion(cur_quat))
        target_quat = (Rotation.from_euler('XYZ', target_euler, degrees=False)).as_quat()
        w,x,y,z = target_quat
        target_rotation = (Rotation.from_quat([w, x, y, z])).as_matrix()
        rot_matrix_e = np.dot((target_rotation.transpose()),cur_rotation) - np.dot(cur_rotation.transpose(),target_rotation)
        rot_e = np.array([rot_matrix_e[2, 1], rot_matrix_e[0, 2], rot_matrix_e[1, 0]]) 
        rpy_rates_e = target_rpy_rates - (cur_rpy - self.last_rpy)/control_timestep
        self.last_rpy = cur_rpy
        self.integral_rpy_e = self.integral_rpy_e - rot_e*control_timestep
        self.integral_rpy_e = np.clip(self.integral_rpy_e, -1500., 1500.)
        self.integral_rpy_e[0:2] = np.clip(self.integral_rpy_e[0:2], -1., 1.)
        # PID target torques.
        target_torques = - np.multiply(self.P_COEFF_TOR, rot_e) \
                         + np.multiply(self.D_COEFF_TOR, rpy_rates_e) \
                         + np.multiply(self.I_COEFF_TOR, self.integral_rpy_e)
        target_torques = np.clip(target_torques, -3200, 3200)
        pwm = thrust + np.dot(self.MIXER_MATRIX, target_torques)
        pwm = np.clip(pwm, self.MIN_PWM, self.MAX_PWM)
        return self.PWM2RPM_SCALE * pwm + self.PWM2RPM_CONST

def PIDcontrol2normalized(pid_ctrl, env):
    hover_thrust = env.hover_thrust
    return (pid_ctrl / hover_thrust - 1) / env.norm_act_scale

if __name__ == "__main__":
    main()