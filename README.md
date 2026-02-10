# Derby v0.5.0 _db2_

Derby is a 100% local time-tracking app written in Python with a GUI built in PyQt. It is designed to be feature-competitive with all other time-tracking applications that I have ever used, especially with their paid versions, which I have always felt were subjected to insane markups because of the demand from lawyers. Fortunately, this application should be well-suited for even use by said lawyers, if they can get past the fact that it is built with the last decade's GUI technology, and only built in that way because it's some of the only computer language that I can speak -- and barely, at that. Derby's notable features include:

- The ability to store hundreds of different projects, and data for them
- Capable of running several projects concurrently, as well as pausing them
- A second type of project called "Background Tasks" you can use to track your second-screen habits, your music listening, or whatever else you might want to
- The ability to view all past sessions in order sorted by end time
- A summary tab for viewing data from today, this week, this month, last month, and all time (I would not recommend clicking that one right now!) with configurable row borders
- The ability to tag projects with several different tags, assign them a priority level, and sort projects by these tags and priority levels in the summary tab
- Dark mode, deep black mode, and light mode visual appearances
- Configurable database location and database backups

You may notice that this is me finally getting around to writing a README by hand, so it's a little barren right now. I'll be adding per-tab sections over the coming days. I don't think many people are using Derby right now anyways, but if more do, I'll be very happy to more aggressively support it with my time and communication, and especially through better, human-made documentation. It's just now gotten useful enough for me to think about things like that, anyways.

## Installation

You have two options for installation: **manual** and **less manual.**

### Manual Installation

Download the source code and unzip it. You will need the latest version of Python 3 available, and pip. Navigate to the unzipped folder in the terminal after you've moved it to wherever you want Derby to live on your computer. Install requirements with this command:

pip install -r requirements.txt

You can do it in a virtual environment if you like, but it pretty much just installs PyQt6. After you're done, run the following command. 

pyinstaller --onefile gui.py --name derby --icon=jockey.ico --noconsole

This outputs a derby executable in the /dist folder. Next, it is very important that you **copy themes.json and jockey.ico to this directory.** The themes json is required for the app to even load (for some reason -- I should fix that) and the jockey icon ensures the app icon shows properly in the top left when running it. 

You can create a shortcut to the produced executable for use wherever.

### Less Manual Installation

Download the non-source-code files from the latest release on Github. Then, make a directory anywhere you want for running the application, and make sure it has the Derby executable, the themes.json, _and_ the jockey.ico. Lastly, create a shortcut for using this executable in this folder from your desktop, and move said shortcut to your desktop. 

### For Both Installation Methods

It is recommended that you change the default data output directory, as it defaults to AppData, cluttering up your boot drive. It doesn't make a lot of data, but I imagine if used for a year straight personally, or even three months professionally, it probably would. Remember to back the database up in both .db and .csv form regularly to a separate location as well.

## General Usage

All timer activities done using Derby are done using projects. You can create projects to time in the Projects tab, but you can also just type in whatever you'd like to call a new project into the selector bar in the Timer tab, and then hit start. This will create a new project with the same name. You can click the arrow next to that bar to select from your already-created projects, where they will be sorted by priority to support large numbers of projects (I use about 50). Starting a project through any of these means will spawn a project card in the frame below it, with buttons that allow you to either stop a project, pause a playing project, or play a paused project. 

Don't forget, you can view your data in-app with the Summary tab, and you can configure the appearance of the app, row dividers, and database location in the Appearance tab. You may also view your session history in the aptly-named History tab.