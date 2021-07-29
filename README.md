# Custom PurpleAir weather service for RainMachine

Use the PurpleAir sensor network as a "local weather service"
for your RainMachine irrigation controller. (No need to own a PurpleAir.)


## Why?

[RainMachine] irrigation controllers adapt watering schedules to the exact needs
of your plants, based on weather forecasts and observed weather conditions.
They support a number of weather services, and also allow you to add custom ones.

If you live in an area with microclimates, your local conditions can vary significantly
from the regional forecasts, and the RainMachine will work better with a source
of hyper-local weather data. The best option is a personal weather station with a rain
sensor. In the past it was easy to access a nearby one through Weather Underground.
Unfortunately, now only weather station owners get free WU API access, and the costs
are prohibitive for personal use.

[PurpleAir] makes a (relatively) low cost air quality sensor, and there are tens of
thousands of them installed around the world. The data from these sensors is publicly
available on the [PurpleAir map][purpleair-map] and through a free API.

Besides air quality, PurpleAir's sensors also report three statistics that are
useful for RainMachine's weather engine:
- temperature
- barometric pressure
- relative humidity

So if you own a RainMachine, but don't have your own personal weather station,
you can probably find a nearby PurpleAir sensor to use instead. It won't give you 
hyper-local rainfall info, but it's a pretty decent substitute for the other stats.

This project implements a custom RainMachine weather service that pulls data
from the PurpleAir sensor network.


## Usage

### Installation

You'll add this project's "PurpleAir Parser" to your RainMachine
as a custom weather service.

1. First, find a PurpleAir sensor near you.
   
   On the [PurpleAir sensor map][purpleair-map], zoom into your location,
   find a sensor that looks promising, and get its **sensor id**.
   
   When you click a sensor on the map, its id will appear in the url as a number 
   after `select=`. It's usually 4-6 digits. E.g., if the url shows 
   `https://www.purpleair.com/map?...cC0&select=71775#11/37...`, 
   the sensor id is `71755`.
   
   Tips:
   
    * Zoom all the way into your location. You want a single sensor
      as close to your location as possible.
    * Be sure you're only looking at *outdoor* sensors.
      (Indoor data would really confuse your RainMachine.)
    * When you click the sensor, you'll see a chart with a few days' history.
      Avoid sensors that seem really out of whack with the actual temperatures
      you experienced. (They might be installed in full sun. Or not actually outdoors.)
    * You can change to ºF or ºC in the map controls at bottom left.

2. Download [purpleair_parser.py][purpleair_parser_raw] from this project.
   
   You're just saving the file temporarily to use in the next step. It doesn't matter
   where you save it. (The Downloads folder is fine.)
   
   (You might want to look through the file and reassure yourself it's not doing
   anything evil.)

3. Follow RainMachine's [*Installing other Weather Services*][rainmachine-custom-weather]
   instructions to add the "Custom:PurpleAir" service.
   
   When you get to the "Choose File" part, use the `purpleair_parser.py` file you
   downloaded in step 2.
   
   When you get to the "enable it and configure" part, enter the `sensorId` from
   step 1. Just leave `keyForPrivateSensor` blank, unless want to use your own,
   [private PurpleAir](#private-sensors) sensor. But be sure to check the "Enabled" box.
   
   And when you get to "Developer Local Weather Push," stop. (That's a different topic 
   that doesn't apply.)

4. Click "Refresh All" at the top of the Weather Services section.

   If everything is working, *after a few moments* the status column will change to 
   "Success." If you get an error message, see [Troubleshooting](#troubleshooting) below.
 
5. In the Weather Sensitivity section (above Weather Services on the same page),
   be sure to enable "Forecast Correction." That tells the RainMachine to use the
   PurpleAir's actual observed conditions to improve the forecast data.


### Uninstallation

To get rid of the PurpleAir custom weather service: go to your RainMachine's
Settings > Weather, scroll down to Weather Services, click the User Uploaded tab, 
click "Custom: PurpleAir", and then click the red "Delete" button.


### Updating

If there's a new version of this script, you'll need to uninstall the old one first.
(This doesn't delete past data or settings.)

1. Uninstall (see [above](#uninstallation))
2. Refresh your browser (if you skip this, the next step may fail)
3. Upload the new version as in [Installation](#installation)


### Troubleshooting

In the RainMachine's Settings > Weather > Weather Services section > User Uploaded tab,
the Status column for "Custom:PurpleAir" should normally show a green "Success."

If the status is "Never," click "Refresh All," then *wait a few moments.*
The status should change.

If the status is a red error, probably it will explain what's going wrong,
and hopefully it's obvious what to do about it.

If the status says "check logs," go to Settings > About, scroll down to the very
bottom, and click "View Log" to open a new window with RainMachine logs.
Search for "PurpleAir" to find more information that may be helpful.

If you have trouble getting settings to stick, try clicking the "Defaults" button 
in Custom:PurpleAir configuration. Then refresh your browser and try entering
the settings again.

If all else fails, try re-installing the PurpleAir custom weather service: 
first [uninstall](#uninstallation), then *refresh your browser*, 
then [install](#installation) the script again.


### Private sensors

If you own a PurpleAir sensor but have kept it private, you should still be able to use
it with this project. The `keyForPrivateSensor` you need is included in the 
"PurpleAir Registration" email you received after setup. 

Look for the "Download data" link in the email. If the link is something like
`https://www.purpleair.com/sensorlist?show=12345&key=ABCDEO1234FGHIJK"`,
then the `sensorId` is `12345` and the `keyForPrivateSensor` is `ABCDEO1234FGHIJK`.


## Developing

Bug reports and pull requests are welcome.

For bug reports, please be sure to include everything mentioning "PurpleAir" in
your RainMachine logs (Settings > About > View Log), as well as your RainMachine
model and firmware version, and which PurpleAir sensorId you're using (if public).

As of July, 2021, RainMachine firmware runs Python 2.7.
You'll need that old version of Python to work on this.
(Newer models on firmware 4.0.1152 run Python 2.7.14, 
and older ones on firmware 4.0.1003 run Python 2.7.3.)

To develop, clone this repository. 
The [RainMachine SDK][rainmachine-sdk] is required,
and can be installed as a git submodule:

```sh
# Get the RainMachine SDK: 
git submodule init
git submodule update
```

To run the tests, make sure you're running Python 2.7 (e.g., via virtualenv), and:

```sh
# Install packages needed for running tests:
pip install -r requirements-test.txt

# Tell Python where to find the RainMachine SDK:
export PYTHONPATH=.:./rainmachine-developer-resources/sdk-parsers

# Run the tests:
python -m unittest discover -s ./test -t .
```


[purpleair_parser_raw]: https://raw.githubusercontent.com/medmunds/rainmachine-weather-purpleair/main/purpleair_parser.py 
[PurpleAir]: https://www2.purpleair.com/
[purpleair-map]: https://www.purpleair.com/map?opt=1/m/i/mTEMP_C/a10/cC0#1.06/-8/-2.1
[RainMachine]: https://rainmachine.com/
[rainmachine-custom-weather]: https://support.rainmachine.com/hc/en-us/articles/360011755813-RainMachine-Weather-Engine#h_cbe8605c-72aa-45cf-8e7f-9e67411e4179
[rainmachine-dev]: https://support.rainmachine.com/hc/en-us/articles/228652608-Developing-with-RainMachine-SDK
[rainmachine-dev-weather]: https://support.rainmachine.com/hc/en-us/articles/228620727-How-to-integrate-RainMachine-with-different-weather-forecast-services
[rainmachine-sdk]: https://github.com/sprinkler/rainmachine-developer-resources
