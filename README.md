This is a utility for making maps of visitors. It takes an excel file, asks you which column is for the addresses, and uses [OpenStreetMap](https://www.openstreetmap.org/) to get the locations of each address, then plots these locations onto a map of the world.

When you click the "make map" button, it will automatically open your default browser and display the map. If you wish to save the map, you can click file > save in your browser and save it as an html file.

# Building from source
To build from source, make sure you have installed [python 3](https://www.python.org/), then run the following commands:
```
# Set up your virual environment
python -mvenv virt
./virt/bin/activate

# Install all of the required dependencies for this project.
python -mpip install -r requirements.txt

# Create an executable.
python -mPyInstaller --onefile plot_visitors.py
```
The executable will be located in the ```dist``` folder.
