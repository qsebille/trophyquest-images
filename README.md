# TrophyQuest Images

This Python Lambda copies images to the dedicated TrophyQuest S3 bucket and stores their HTTPS URLs in PostgreSQL. The API prefers the stored copy and falls back to the source URL.

| Images | Eligible records |
| --- | --- |
| PSN player avatars, trophy suite images and trophy icons | All records with a source URL |
| IGDB covers, backgrounds and screenshots | Games linked to at least one PSN suite by an automatic or manual match |

Candidate-only covers are served from IGDB in the association screen until the game is linked to a suite.

## Deploy and run

Pull requests to `main` use the same title check and Python test workflow as `trophyquest-igdb`. A merged PR creates a SemVer tag and deploys that commit to the Lambda. Configure the GitHub repository variables `AWS_ROLE_ARN` and `AWS_REGION` for this repository's OIDC deployment role.

Before merging the first deployment PR, provision the `trophyquest-image-uploader` function as a Python ZIP Lambda with handler `image_uploader.handler.image_uploader_handler`. Publish an initial function version and create the `prod` alias so the deployment workflow can update it. Configure the runtime, execution role and network access to PostgreSQL and the image sources. Apply the web service's image cache migration before invoking the function. Point scheduled invocations at the `prod` alias.

| Lambda environment variable | Value |
| --- | --- |
| `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DATABASE`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | PostgreSQL connection details |
| `IMAGES_BUCKET_NAME` | The dedicated S3 bucket, `trophyquest-images` in `eu-west-3` |
| `IMAGES_PUBLIC_BASE_URL` | Optional HTTPS base URL for serving the objects. Defaults to `https://<bucket>.s3.amazonaws.com`. |
| `IMAGES_MAX_WORKERS` | Concurrent uploads, defaults to 16 |

The Lambda execution role needs `s3:PutObject` on the image objects. Its database user needs to read the image sources and IGDB matches and update the AWS URL columns. Verify that the configured HTTPS base URL serves those objects to browsers.

The invocation payload accepts `player_avatar_limit`, `trophy_suite_image_limit`, `trophy_icon_limit` and `igdb_image_limit`. The IGDB limit applies to all three IGDB image types combined. Each defaults to 20. A value of 0 skips that batch.

## Test locally

```bash
python -m pip install -r requirements.txt pytest
PYTHONPATH=src python -m pytest tests
```
