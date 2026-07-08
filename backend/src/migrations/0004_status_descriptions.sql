UPDATE image_statuses SET description = CASE
    WHEN title = 'hidden' THEN 'This is the initial status of an image after upload. It will not be visible to users unless you add it to a pair.'
    WHEN title = 'open' THEN 'The image is now open to use for annotation'
    WHEN title = 'review_pending' THEN 'The image is set to be reviewed for finalization by a scientist or admin user'
    WHEN title = 'finalized' THEN 'Review complete, no further changes to the image'
    WHEN title = 'deleted' THEN 'Marked as deleted. The underlying image file may be deleted. Record kept in database for tracability'
END
WHERE title IN ('hidden', 'open', 'review_pending', 'finalized', 'deleted');

UPDATE pair_statuses SET description = CASE
    WHEN title = 'hidden' THEN 'Not visible to users yet. This allows releasing candidates in batches to the users to keep the annotations dense.'
    WHEN title = 'open' THEN 'Open for review and editing'
    WHEN title = 'review_pending' THEN 'Awaiting review for finalization, no more annotations at this stage until set back to open'
    WHEN title = 'finalized' THEN 'Review complete, no further annotations for this pair.'
    WHEN title = 'deleted' THEN 'Marked as deleted. Record kept in database for tracability'
END
WHERE title IN ('hidden', 'open', 'review_pending', 'finalized', 'deleted');

UPDATE candidate_statuses SET description = CASE
    WHEN title = 'hidden' THEN 'Not visible to users yet. This allows releasing candidates in batches to the users to keep the annotations dense.'
    WHEN title = 'open' THEN 'Open for annotations by users.'
    WHEN title = 'no_overlap' THEN 'Enough annotations marked this candidate pair to have no overlap. No more candidate annotations possible in this status. Candidate pair will not be used for point annotations.'
    WHEN title = 'has_overlap' THEN 'Enough annotations marked this candidate pair to have an overlap. No more candidate annotations possible in this status. When set to this status, an image pair for point annotations is created with status "hidden"'
    WHEN title = 'deleted' THEN 'Marked as deleted. No more annotations possible.'
END
WHERE title IN ('hidden', 'open', 'no_overlap', 'has_overlap', 'deleted');

UPDATE annotation_statuses SET description = CASE
    WHEN title = 'review_pending' THEN 'Awaiting review. Within a short time of creation, the creator can correct their annotation.'
    WHEN title = 'review_failed' THEN 'Review did not pass and the annotation is treated as deleted.'
    WHEN title = 'approved' THEN 'Review approved and annotation is accepted as "good"'
    WHEN title = 'overwritten' THEN 'Superseded by newer annotation, but is kept as a tombstone record. This is set outside the review process.'
    WHEN title = 'deleted' THEN 'Marked as deleted. This is set outside the review process.'
END
WHERE title IN ('review_pending', 'review_failed', 'approved', 'overwritten', 'deleted');
