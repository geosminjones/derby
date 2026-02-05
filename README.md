# Derby v0.5.0 db1

Derby is a 100% local time-tracking app written in Python with a GUI built in CustomTkinter. It is designed to be feature-competitive with all other time-tracking applications that I have ever used, especially with their paid versions, which I have always felt were subjected to insane markups because of the demand from lawyers. Fortunately, this application should be well-suited for even use by said lawyers, if they can get past the fact that it is built with the last decade's GUI technology, and only built in that way because it's some of the only computer language that I can speak -- and barely, at that. Derby's notable features include:

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

The packaged Derby executables are compiled by me in a virtual environment, and I use them extensively on my own Windows machine, so they should generally work. If they do not, let me know, and I'll be on top of it, but otherwise, you can also compile your own executable with the following command, after navigating to the directory post-download and installing requirements:

pyinstaller --onefile gui.py --name derby --icon=jockey.ico --noconsole

This should produce a named executable (albeit without a version number) that doesn't spawn a console and works just fine. It's the command I use on my own machine.

## General Usage

All timer activities done using Derby are done using projects. You can create projects to time in the Projects tab, but you can also just type in whatever you'd like to call a new project into the selector bar in the Timer tab, and then hit start. This will create a new project with the same name. You can click the arrow next to that bar to select from your already-created projects, where they will be sorted by priority to support large numbers of projects (I use about 50). Starting a project through any of these means will spawn a project card in the frame below it, with buttons that allow you to either stop a project, pause a playing project, or play a paused project. 

Don't forget, you can view your data in-app with the Summary tab, and you can configure the appearance of the app, row dividers, and database location in the Appearance tab. You may also view your session history in the aptly-named History tab.