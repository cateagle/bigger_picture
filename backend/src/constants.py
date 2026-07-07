from enum import StrEnum


class Role(StrEnum):
    ANNOTATOR = "annotator"
    SCIENTIST = "scientist"
    ADMIN = "admin"


ROLE_RANK: dict[str, int] = {
    Role.ANNOTATOR: 0,
    Role.SCIENTIST: 1,
    Role.ADMIN: 2,
}


class AnnotationStatus(StrEnum):
    REVIEW_PENDING = "review_pending"
    REVIEW_FAILED = "review_failed"
    APPROVED = "approved"
    OVERWRITTEN = "overwritten"
    DELETED = "deleted"


ANNOTATION_STATUS_INT: dict[str, int] = {
    AnnotationStatus.REVIEW_PENDING: 0,
    AnnotationStatus.REVIEW_FAILED: 1,
    AnnotationStatus.APPROVED: 2,
    AnnotationStatus.OVERWRITTEN: 3,
    AnnotationStatus.DELETED: 4,
}

INT_ANNOTATION_STATUS: dict[int, AnnotationStatus] = {
    0: AnnotationStatus.REVIEW_PENDING,
    1: AnnotationStatus.REVIEW_FAILED,
    2: AnnotationStatus.APPROVED,
    3: AnnotationStatus.OVERWRITTEN,
    4: AnnotationStatus.DELETED,
}


class ImageStatus(StrEnum):
    HIDDEN = "hidden"
    OPEN = "open"
    REVIEW_PENDING = "review_pending"
    FINALIZED = "finalized"
    DELETED = "deleted"


IMAGE_STATUS_INT: dict[str, int] = {
    ImageStatus.HIDDEN: 0,
    ImageStatus.OPEN: 1,
    ImageStatus.REVIEW_PENDING: 2,
    ImageStatus.FINALIZED: 3,
    ImageStatus.DELETED: 4,
}

INT_IMAGE_STATUS: dict[int, ImageStatus] = {
    0: ImageStatus.HIDDEN,
    1: ImageStatus.OPEN,
    2: ImageStatus.REVIEW_PENDING,
    3: ImageStatus.FINALIZED,
    4: ImageStatus.DELETED,
}


class PairStatus(StrEnum):
    HIDDEN = "hidden"
    OPEN = "open"
    REVIEW_PENDING = "review_pending"
    FINALIZED = "finalized"
    DELETED = "deleted"


PAIR_STATUS_INT: dict[str, int] = {
    PairStatus.HIDDEN: 0,
    PairStatus.OPEN: 1,
    PairStatus.REVIEW_PENDING: 2,
    PairStatus.FINALIZED: 3,
    PairStatus.DELETED: 4,
}

INT_PAIR_STATUS: dict[int, PairStatus] = {
    0: PairStatus.HIDDEN,
    1: PairStatus.OPEN,
    2: PairStatus.REVIEW_PENDING,
    3: PairStatus.FINALIZED,
    4: PairStatus.DELETED,
}


class CandidateStatus(StrEnum):
    HIDDEN = "hidden"
    OPEN = "open"
    NO_OVERLAP = "no_overlap"
    HAS_OVERLAP = "has_overlap"
    DELETED = "deleted"


CANDIDATE_STATUS_INT: dict[str, int] = {
    CandidateStatus.HIDDEN: 0,
    CandidateStatus.OPEN: 1,
    CandidateStatus.NO_OVERLAP: 2,
    CandidateStatus.HAS_OVERLAP: 3,
    CandidateStatus.DELETED: 4,
}

INT_CANDIDATE_STATUS: dict[int, CandidateStatus] = {
    0: CandidateStatus.HIDDEN,
    1: CandidateStatus.OPEN,
    2: CandidateStatus.NO_OVERLAP,
    3: CandidateStatus.HAS_OVERLAP,
    4: CandidateStatus.DELETED,
}
