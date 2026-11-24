# TrophyQuest Images

This Python Lambda copies images to the dedicated TrophyQuest S3 bucket and stores their HTTPS URLs in PostgreSQL. The API prefers the stored copy and falls back to the source URL.

| Images | Eligible records |
| --- | --- |
| PSN player avatars, trophy suite images and trophy icons | All records with a source URL |
| IGDB covers, backgrounds and screenshots | Games linked to at least one PSN suite by an automatic or manual match |

Candidate-only covers are served from IGDB in the association screen until the game is linked to a suite.

## Deploy and run

Pull requests to `main` use the same title check and Python test workflow as `trophyquest-igdb`. A merged PR creates a SemVer tag and deploys that commit to the Lambda. Configure `AWS_ROLE_ARN` and `AWS_REGION` in the GitHub `prod` deployment environment.

Before merging the first deployment PR, follow the infrastructure repository's image uploader instructions to provision the Lambda, publish its initial version and create the `prod` alias. Build the initial Python 3.12 ARM64 ZIP with `bash scripts/package-lambda.sh 3.12 arm64`. The ZIP is written to `out/image-uploader.zip`.

| Lambda environment variable | Value |
| --- | --- |
| `POSTGRES_SECRET_ARN` | Production Secrets Manager secret containing JSON with `host`, `port`, `dbname`, `username` and `password`. The function refreshes its cached credentials every five minutes. |
| `IMAGES_BUCKET_NAME` | The dedicated S3 bucket, `trophyquest-images` in `eu-west-3` |
| `IMAGES_PUBLIC_BASE_URL` | Optional HTTPS base URL for serving the objects. Defaults to `https://<bucket>.s3.amazonaws.com`. |
| `IMAGES_MAX_WORKERS` | Concurrent uploads, defaults to 16 |

The Lambda execution role needs `s3:PutObject` on the image objects and `secretsmanager:GetSecretValue` on the database secret. Its database user needs to read the image sources and IGDB matches and update the AWS URL columns. Verify that the configured HTTPS base URL serves those objects to browsers. For local execution, leave `POSTGRES_SECRET_ARN` unset and use `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DATABASE`, `POSTGRES_USER` and `POSTGRES_PASSWORD`.

The invocation payload accepts `player_avatar_limit`, `trophy_suite_image_limit`, `trophy_icon_limit` and `igdb_image_limit`. The IGDB limit applies to all three IGDB image types combined. Each defaults to 20. A value of 0 skips that batch.

## Test locally

```bash
python -m pip install -r requirements.txt pytest
PYTHONPATH=src python -m pytest tests
```
