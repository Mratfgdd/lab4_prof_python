class StudentError(Exception):
    pass


class InvalidGradeError(StudentError, ValueError):
    pass


class InvalidGroupCodeError(StudentError, ValueError):
    pass


class InvalidStudentDataError(StudentError, ValueError):
    pass


class StudentNotFoundError(StudentError, LookupError):
    pass


class GroupNotFoundError(StudentError, LookupError):
    pass


class DuplicateKeyError(StudentError, ValueError):
    pass
