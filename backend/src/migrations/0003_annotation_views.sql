CREATE VIEW view_point_annotation_flat AS
SELECT
    pa.id,
    pa.uuid,

    pa.created_at,
    cu.username AS created_by,

    pa.expert_level,
    pa.confidence,

    ast.title AS annotation_status,

    pa.reviewed_at,
    ru.username AS reviewed_by,

    l.uuid  AS label_uuid,
    l.scope AS label_scope,
    l.title AS label_title,

    ip.id AS pair_id,
    ip.created_at AS pair_created_at,
    pcu.username AS pair_created_by,
    ip.difficulty AS pair_difficulty,
    ip.priority AS pair_priority,
    pst.title AS pair_status,

    i1.uuid AS image1_uuid,
    i1.filename AS image1_filename,
    i1.filepath AS image1_filepath,
    ist1.title AS image1_status,
    i1.size_x AS image1_size_x,
    i1.size_y AS image1_size_y,
    i1.difficulty AS image1_difficulty,
    i1.priority AS image1_priority,

    i2.uuid AS image2_uuid,
    i2.filename AS image2_filename,
    i2.filepath AS image2_filepath,
    ist2.title AS image2_status,
    i2.size_x AS image2_size_x,
    i2.size_y AS image2_size_y,
    i2.difficulty AS image2_difficulty,
    i2.priority AS image2_priority,

    d.uuid AS dive_uuid,
    d.title AS dive_title,

    pa.x1,
    pa.y1,
    pa.x2,
    pa.y2

FROM point_annotations pa

JOIN users cu
    ON cu.id = pa.created_by
LEFT JOIN users ru
    ON ru.id = pa.reviewed_by

LEFT JOIN labels l
    ON l.id = pa.label_id

JOIN annotation_statuses ast
    ON ast.id = pa.status_id

JOIN image_pairs ip
    ON ip.id = pa.pair_id

JOIN users pcu
    ON pcu.id = ip.created_by

LEFT JOIN pair_statuses pst
    ON pst.id = ip.status_id

JOIN images i1
    ON i1.id = ip.image1_id
JOIN images i2
    ON i2.id = ip.image2_id

LEFT JOIN image_statuses ist1
    ON ist1.id = i1.status_id
LEFT JOIN image_statuses ist2
    ON ist2.id = i2.status_id

JOIN dives d
    ON d.id = i1.dive_id;


CREATE VIEW view_candidate_annotation_flat AS
SELECT
    ca.id,
    ca.uuid,

    ca.created_at,
    cu.username AS created_by,

    ca.no_overlap,
    ca.expert_level,

    ast.title AS annotation_status,

    ca.reviewed_at,
    ru.username AS reviewed_by,

    cp.id AS candidate_pair_id,
    cp.created_at AS candidate_created_at,
    cpu.username AS candidate_created_by,
    cst.title AS candidate_status,

    i1.uuid AS image1_uuid,
    i1.filename AS image1_filename,
    i1.filepath AS image1_filepath,
    ist1.title AS image1_status,
    i1.size_x AS image1_size_x,
    i1.size_y AS image1_size_y,
    i1.difficulty AS image1_difficulty,
    i1.priority AS image1_priority,

    i2.uuid AS image2_uuid,
    i2.filename AS image2_filename,
    i2.filepath AS image2_filepath,
    ist2.title AS image2_status,
    i2.size_x AS image2_size_x,
    i2.size_y AS image2_size_y,
    i2.difficulty AS image2_difficulty,
    i2.priority AS image2_priority,

    d.uuid AS dive_uuid,
    d.title AS dive_title

FROM candidate_annotations ca

JOIN users cu
    ON cu.id = ca.created_by
LEFT JOIN users ru
    ON ru.id = ca.reviewed_by

JOIN annotation_statuses ast
    ON ast.id = ca.status_id

JOIN candidate_pairs cp
    ON cp.id = ca.candidate_id

JOIN users cpu
    ON cpu.id = cp.created_by

JOIN candidate_statuses cst
    ON cst.id = cp.status_id

JOIN images i1
    ON i1.id = cp.image1_id
JOIN images i2
    ON i2.id = cp.image2_id

LEFT JOIN image_statuses ist1
    ON ist1.id = i1.status_id
LEFT JOIN image_statuses ist2
    ON ist2.id = i2.status_id

JOIN dives d
    ON d.id = i1.dive_id;
