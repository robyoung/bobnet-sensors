from setuptools import setup

tests_require = [
    'pytest',
    'pytest-cov'
]

dev_requires = [
    'ipython==6.2.1'
]

setup_requires = [
    'pytest-runner'
]

setup(
    name='bobnet-sensors',
    version='0.1.0',
    description='Package for running bobnet sensor nodes',
    author='Rob Young',
    author_email='rob@robyoung.digital',
    packages=['bobnet_sensors'],

    install_requires=[
        'PyYAML==3.12',
        'paho-mqtt==1.3.1',
        'pyjwt==1.5.3',
        'cryptography==2.1.3',
        'gpiozero==1.4.0',
        'RPi.GPIO==0.6.3',
    ],

    setup_requires=setup_requires,
    tests_require=tests_require,

    extras_require={
        'dev': dev_requires + tests_require + setup_requires
    },

    entry_points={
        'console_scripts': [
            'bobnet-sensors = bobnet_sensors.cli:main'
        ]
    }
)
