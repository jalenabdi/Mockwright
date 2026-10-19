"""Exceptions raised by the interview service.

All exceptions share a common base, InterviewServiceError, so callers (such
as the routes layer) can catch one type if they want, or map each specific
subclass to its own HTTP status code.

Suggested HTTP mapping for whoever builds the route on top of this service:

    InterviewNotFoundError          -> 404
    InterviewAlreadyCompletedError  -> 409
    QuestionNotInInterviewError     -> 404 or 422
    QuestionOutOfOrderError         -> 409
    AnswerAlreadyExistsError        -> 409
    BlankAnswerError                -> 422
"""


class InterviewServiceError(Exception):
    """Base class for all interview service errors."""


class InterviewNotFoundError(InterviewServiceError):
    """No interview exists for the given interview_id."""


class InterviewAlreadyCompletedError(InterviewServiceError):
    """An answer was submitted to an interview that is already completed."""


class QuestionNotInInterviewError(InterviewServiceError):
    """question_id does not exist, or belongs to a different interview."""


class QuestionOutOfOrderError(InterviewServiceError):
    """question_id is not the interview's current question."""


class AnswerAlreadyExistsError(InterviewServiceError):
    """The question already has an answer saved."""


class BlankAnswerError(InterviewServiceError):
    """answer_text is empty or whitespace-only."""
