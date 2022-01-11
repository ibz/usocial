#!/usr/bin/env bash

IMAGE_NAME=${1}
VERSION=${2}
BASE_IMAGE=${3}
FINAL_NAME="${IMAGE_NAME}:${VERSION}-${BASE_IMAGE}"
MANIFEST_NAME="${FINAL_NAME}"

declare -a architectures=("amd64" "arm64")

for architecture in "${architectures[@]}"; do
  echo "Pulling ${VERSION} for ${architecture}..."
  docker pull "${FINAL_NAME}-${architecture}"
done

echo "Creating manifest list..."
for architecture in "${architectures[@]}"; do
  echo " ${FINAL_NAME}-${architecture}"
done | xargs docker manifest create "${MANIFEST_NAME}"

for architecture in "${architectures[@]}"; do
  echo "Annotating manifest for ${architecture}..."
  docker manifest annotate "${MANIFEST_NAME}" "${FINAL_NAME}-${architecture}" --arch ${architecture} --os linux
done

echo "Pushing manifest list..."
docker manifest push --purge ${MANIFEST_NAME}
