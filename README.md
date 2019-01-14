Velbus HTTP interface
=====================

This project is an HTTP(s) interface to the [Velbus] domotica system.

[Velbus]: https://www.velbus.eu/


Quickstart
----------

1. Clone this repository
2. Create a new Python [VirtualEnv] (optional, but highly recommended):

   ```bash
   $ python3 -m venv venv
   $ source venv/bin/activate
   (venv) $
   ```
3. Install `structattr`:

   ```bash
   (venv) $ pip install git+https://github.com/niobos/structattr.git
   ```

4. Install `velbuspi`:

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
