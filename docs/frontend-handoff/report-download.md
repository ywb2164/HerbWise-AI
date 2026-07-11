# Soybean Admin report download

Call the export endpoint, store `report_id`, then download `/api/reports/{report_id}/download`. A 404 means the generated file is absent; do not construct a file path client-side.
