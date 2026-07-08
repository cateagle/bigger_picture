CREATE UNIQUE INDEX IF NOT EXISTS idx_candidate_annotations_candidate_user
ON candidate_annotations (candidate_id, created_by);