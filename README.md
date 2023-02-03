Usage:
1: python mainStep1_PwFeed.py 
    - fill the last year/month inside the main function
    - newer months are before older months
    - do not generate xml for months that already have been generated

2: mainStep2_xml_combine_episodes.bat # extract only the episodes to file output\paulwhite_year_month.xml
    - put newest months on top
    - do not uncomment older months
    - the result goes to file output\latest_episodes.xml

3: Copy all xml items (episodes) to relevant files:
    - allEpisodesFeed.xml
    - allEpisodes_CopyFromHere.xml
