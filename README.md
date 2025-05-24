# DEV BRANCH
This branch is for development.
When changes work on this branch I will merge with main.

# Project overview

This project aims to create a local app that listens to changes in a codebase and automatically sends changes to a RAG system.
Large language models will suggest changes, stop the developer from making bad desicions, and nudge them in the right direction.

I'm not an opposer for "vide coding". Matter of fact, I'm basically going to "vibe" this entire project myself.
But in the age of exponentially growing AI capabilities, I think it's important for for developers to learn things in the correct order.
There are excellent tools at everyones disposal for boosting productivity but they can easily result in bad code if the developer does not have a good understanding of what good code is supposed to look like.

Ducky aims to bridge the gap between traditional coding and fully automatic coding IDEs by acting more like a mentor looking over your shoulder, telling you to take a step back and provide rubebrducking sessions when the developer gets stuck.

# "I see you're trying to learn more! Want me to tell how it works?"

Ducky is what I decided to call the assitant. 
He has a snapshot of your codebase in a SQLite database stored on your local machine.
When you update your codebase the database gets updated, enabling Ducky to perform RAG tasks to help you imrpove your code.
Large Language Models determines what the change was and if it needs to be commented on.
If you start to write inconsistent, smelly or down right bad practices, Ducky will let you know and invite you to talk about it.

Ducky won't (in this stage of development at least) write code for you.
He is simply there to prove oversight and help you understand what you did wrong and how to improve it.
I do not aim to make another autocomplete or code generator, I believe there are several tools that does this perfectly well already!
