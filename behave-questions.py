import random

behavioral_questions = [
    "Tell me about a time you had to deal with a difficult teammate or stakeholder. How did you handle the situation?",
    "Describe a challenging project you worked on. What obstacles did you face, and how did you overcome them?",
    "Give an example of a time you failed or made a mistake at work or school. What did you learn from it?",
    "Tell me about a time you had to work under a tight deadline with incomplete information. How did you prioritize your tasks?",
    "Describe a situation where you had to persuade someone to see things your way or accept your proposal.",
    "Tell me about a time you had to adapt quickly to a major change in project requirements or team direction.",
    "Give an example of a time you took initiative on a project without being explicitly asked by a lead or manager.",
    "Describe a complex problem you solved recently. How did you break it down and decide on your approach?",
    "Tell me about a time you received critical or constructive feedback. How did you react and apply that feedback?",
    "Describe a time you had to balance multiple competing priorities at once. How did you manage your time and expectations?"
    ] 

def get_random_behavioral_question(count : int = 5):
    """
    Returns a list of random behavioral questions.
    """
    return random.sample(behavioral_questions, k=count)

random_behavioral_questions = get_random_behavioral_question() 

def print_random_behavioral_questions():
    """
    Prints a list of random behavioral questions.
    """
    for random_behavioral_question in random_behavioral_questions:
        print(random_behavioral_question)
