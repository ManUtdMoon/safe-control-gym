from setuptools import setup

setup(name='safe_control_gym',
    version='0.5.0',
    install_requires=[
        'matplotlib', 
        'Pillow', 
        'munch', 
        'pyyaml', 
        'imageio', 
        'dict-deep',
        'scikit-optimize', 
        'pandas', 
        'gym~=0.24.0', 
        'torch', 
        'gpytorch', 
        'ray',
        'tensorboard', 
        'casadi', 
        'pybullet',
        'cvxpy', 
        'pytope', 
        'Mosek'
        ]
)
