Velbus HTTP interface
=====================

This project is an HTTP(s) interface to the [Velbus] domotica system.

[Velbus]: https://www.velbus.eu/


Dependencies
------------

On debian:

 * `python3` 3.7 or higher (default on buster, not supported on stretch)
 * `build-essential`, `python3-dev` to compile C-extensions for some of the Python dependencies
 * (optional) `nodejs` and `npm` for the React Web Frontend


Quickstart
----------

1. Clone this repository

   ```bash
   git clone https://github.com/niobos/velbuspy.git
   cd velbuspy
   ```

2. Create a new Python [VirtualEnv] (optional, but highly recommended) and make
   sure you have current setuptools and wheels:

   ```bash
   $ python3 -m venv venv
   $ source venv/bin/activate
   (venv) $ pip install setuptools wheel
   ```
3. Install `structattr`:

   ```bash
   (venv) $ pip install git+https://github.com/niobos/structattr.git
   ```

4. Install `velbuspy`:

   ```bash
   (venv) $ pip install -e .
   ```

5. (Optional): install and build the React Web Frontend:

   ```bash
   (venv) $ git clone https://github.com/niobos/velbusjs.git
   (venv) $ cd velbusjs
   (venv) $ $EDITOR public/index.html
   (venv) $ npm install
   (venv) $ npm run build
   ```

6. Run the daemon for `/dev/ttyUSB0` (substitute for the port actually in use)

   ```bash
   (venv) $ python src/run.py --static-dir velbusjs/build /dev/ttyUSB0
   ```

7. Point your browser to http://localhost:8080/

[VirtualEnv]: https://virtualenv.pypa.io/en/latest/


Debugging tips
--------------

You can fake a serial port with `socat`: `socat -d -d PTY -`
