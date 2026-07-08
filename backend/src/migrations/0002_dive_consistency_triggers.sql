CREATE TRIGGER trg_image_pairs_same_dive_insert
BEFORE INSERT ON image_pairs
FOR EACH ROW
WHEN (
    SELECT dive_id FROM images WHERE id = NEW.image1_id
) <> (
    SELECT dive_id FROM images WHERE id = NEW.image2_id
)
BEGIN
    SELECT RAISE(ABORT, 'Both images in an image pair must belong to the same dive');
END;


CREATE TRIGGER trg_image_pairs_same_dive_update
BEFORE UPDATE OF image1_id, image2_id ON image_pairs
FOR EACH ROW
WHEN (
    SELECT dive_id FROM images WHERE id = NEW.image1_id
) <> (
    SELECT dive_id FROM images WHERE id = NEW.image2_id
)
BEGIN
    SELECT RAISE(ABORT, 'Both images in an image pair must belong to the same dive');
END;


CREATE TRIGGER trg_candidate_pairs_same_dive_insert
BEFORE INSERT ON candidate_pairs
FOR EACH ROW
WHEN (
    SELECT dive_id FROM images WHERE id = NEW.image1_id
) <> (
    SELECT dive_id FROM images WHERE id = NEW.image2_id
)
BEGIN
    SELECT RAISE(ABORT, 'Both images in a candidate pair must belong to the same dive');
END;


CREATE TRIGGER trg_candidate_pairs_same_dive_update
BEFORE UPDATE OF image1_id, image2_id ON candidate_pairs
FOR EACH ROW
WHEN (
    SELECT dive_id FROM images WHERE id = NEW.image1_id
) <> (
    SELECT dive_id FROM images WHERE id = NEW.image2_id
)
BEGIN
    SELECT RAISE(ABORT, 'Both images in a candidate pair must belong to the same dive');
END;
