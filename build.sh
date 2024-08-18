#!/usr/bin/env bash

# Название и версия пакета
BUILD_DIR='.build'
PACKAGE_NAME="windwatch"
RUN_USER="root"
MAINTAINER="zcoder <zhen.pub@gmail.com>"
DESCRIPTION="WindWatch - A tool for monitoring and managing active windows, and help prevent wind inside mind (~.~)"
if [ -z "$VERSION" ];
then
  VERSION="1.0.1"
fi;
LOG_DIR="/var/log/windwatch"
SERVICE_LOG="${LOG_DIR}/windwatch_service.log"
APP_LOG="${LOG_DIR}/windwatch_apps.log"
SERVICE_CONF="/etc/windwatch/windwatch.json"

# Создаем структуру каталогов
if [[ "${BUILD_DIR}" == ".build" && -d "./${BUILD_DIR}" ]];
then
  rm -rf "./${BUILD_DIR}/"
fi;

mkdir -p ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}/usr/local/bin
mkdir -p ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}/etc/windwatch
mkdir -p ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}/etc/systemd/system
mkdir -p ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}/var/log/windwatch
mkdir -p ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}/DEBIAN

# Копируем файлы скрипта и конфигурации
cp windwatch.py ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}/usr/local/bin/
cp windwatch.json ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}/etc/windwatch/

# Создаем файл сервиса systemd
cat <<EOF > ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}/etc/systemd/system/windwatch.service
[Unit]
Description=$DESCRIPTION
After=graphical.target

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/windwatch.py --config $SERVICE_CONF
WorkingDirectory=/usr/local/bin/
Restart=on-failure
User=$RUN_USER
Environment=PYTHONUNBUFFERED=1
StandardOutput=append:$SERVICE_LOG
StandardError=append:$SERVICE_LOG

[Install]
WantedBy=graphical.target

EOF

# Создаем файл управления пакетом (control)
cat <<EOF > ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}/DEBIAN/control
Package: $PACKAGE_NAME
Version: $VERSION
Section: base
Priority: optional
Architecture: all
Depends: python3, xdotool, python3-tz
Maintainer: $MAINTAINER
Description: $DESCRIPTION
EOF

# Создаем скрипт postinst для автоматической активации сервиса после установки
cat <<EOF > ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}/DEBIAN/postinst
#!/usr/bin/env bash

# Создаем лог файл
touch ${APP_LOG}
touch ${SERVICE_LOG}

systemctl daemon-reload
systemctl enable windwatch.service
systemctl start windwatch.service



EOF


cat <<EOF > ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}/DEBIAN/postrm
#!/usr/bin/env bash

# Остановка и отключение сервиса
systemctl stop windwatch.service 2>/dev/null || true
systemctl disable windwatch.service 2>/dev/null || true

# Удаление Unit-файла
rm /etc/systemd/system/windwatch.service 2>/dev/null || true
systemctl daemon-reload 2>/dev/null || true

# Удаление логов
if [[ "${LOG_DIR}" == "/var/log/windwatch" && -d "${LOG_DIR}" ]];
then
  rm -rf "${LOG_DIR}" 2>/dev/null || true
fi;

echo "WindWatch service and associated files have been removed."
EOF

# Делаем postinst исполняемым
chmod 755 ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}/DEBIAN/postinst
chmod 755 ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}/DEBIAN/postrm

# Помечаем конфигурационный файл
echo "/etc/windwatch/windwatch.json" > ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}/DEBIAN/conffiles

# Собираем deb-пакет
dpkg-deb --root-owner-group --build ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}

ln -s ${PACKAGE_NAME}_${VERSION}.deb ${BUILD_DIR}/${PACKAGE_NAME}.deb

echo "Пакет ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}.deb собран успешно."
