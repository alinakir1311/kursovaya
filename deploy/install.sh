#!/usr/bin/env bash
# Initial deployment on the user's empty Ubuntu server.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
export PIP_DEFAULT_TIMEOUT=180
export PIP_RETRIES=10
export PIP_RESUME_RETRIES=10
SITE_IP=177.203.58.14
SOURCE=$(cd "$(dirname "$0")/.." && pwd)
test "$(id -u)" -eq 0
if test -d /opt/avtoritm && ! test -f /opt/avtoritm/.installer-owned; then
    echo "Existing /opt/avtoritm requires inspection before installation."
    exit 1
fi
apt-get update
apt-get install -y python3-venv python3-pip nginx postgresql curl ca-certificates
id avtoritm >/dev/null 2>&1 || useradd --system --home /var/lib/avtoritm --shell /usr/sbin/nologin avtoritm
install -d /opt/avtoritm/app
touch /opt/avtoritm/.installer-owned
for item in config shop static templates manage.py requirements.txt deploy; do
    cp -R "$SOURCE/$item" /opt/avtoritm/app/
done
install -d -o avtoritm -g www-data -m 2750 /var/lib/avtoritm
install -d -o avtoritm -g www-data -m 2750 /var/lib/avtoritm/static /var/lib/avtoritm/media
usermod -a -G www-data avtoritm
python3 -m venv /opt/avtoritm/venv
/opt/avtoritm/venv/bin/pip install -r /opt/avtoritm/app/deploy/requirements.txt
systemctl enable --now postgresql
if ! runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='avtoritm'" | grep -q 1; then
    runuser -u postgres -- createuser avtoritm
fi
if ! runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_database WHERE datname='avtoritm'" | grep -q 1; then
    runuser -u postgres -- createdb -O avtoritm avtoritm
fi
if ! test -f /etc/avtoritm.env || ! grep -qx "SITE_IP=$SITE_IP" /etc/avtoritm.env; then
    (umask 077
    secret=$(python3 -c 'import secrets; print(secrets.token_hex(48))')
    printf 'DJANGO_SETTINGS_MODULE=config.production\nSITE_IP=%s\nDJANGO_SECRET_KEY=%s\n' "$SITE_IP" "$secret" > /etc/avtoritm.env)
fi
set -a
source /etc/avtoritm.env
set +a
cd /opt/avtoritm/app
runuser -u avtoritm -- /opt/avtoritm/venv/bin/python manage.py migrate --noinput
runuser -u avtoritm -- /opt/avtoritm/venv/bin/python manage.py populate_catalog
runuser -u avtoritm -- /opt/avtoritm/venv/bin/python manage.py collectstatic --noinput
runuser -u avtoritm -- /opt/avtoritm/venv/bin/python manage.py check --deploy

# Serve the ACME challenge before enabling HTTPS.
printf 'server_names_hash_bucket_size 64;\n' > /etc/nginx/conf.d/avtoritm-hash.conf
install -d -m 755 /var/www/avtoritm-acme
if ! test -f "/etc/letsencrypt/live/$SITE_IP/fullchain.pem"; then
    cat > /etc/nginx/sites-available/avtoritm <<EOF
server {
    listen 80;
    server_name $SITE_IP;
    location /.well-known/acme-challenge/ { root /var/www/avtoritm-acme; }
    location / { return 503; }
}
EOF
    ln -sfn /etc/nginx/sites-available/avtoritm /etc/nginx/sites-enabled/avtoritm
    nginx -t
    systemctl enable --now nginx
    systemctl reload nginx
fi
python3 -m venv /opt/avtoritm/certbot
/opt/avtoritm/certbot/bin/pip install 'certbot>=5.4,<6'
/opt/avtoritm/certbot/bin/certbot certonly --non-interactive --agree-tos --register-unsafely-without-email --preferred-profile shortlived --webroot --webroot-path /var/www/avtoritm-acme --ip-address "$SITE_IP" --cert-name "$SITE_IP" --keep-until-expiring
sed "s/SITE_IP/$SITE_IP/g" deploy/nginx.conf > /etc/nginx/sites-available/avtoritm
ln -sfn /etc/nginx/sites-available/avtoritm /etc/nginx/sites-enabled/avtoritm
install -m 644 deploy/avtoritm.service /etc/systemd/system/avtoritm.service
cat > /etc/systemd/system/avtoritm-cert-renew.service <<'EOF'
[Unit]
Description=Renew Avtoritm IP certificate
[Service]
Type=oneshot
ExecStart=/opt/avtoritm/certbot/bin/certbot renew --quiet --deploy-hook "/usr/sbin/nginx -t && /usr/bin/systemctl reload nginx"
EOF
cat > /etc/systemd/system/avtoritm-cert-renew.timer <<'EOF'
[Unit]
Description=Check Avtoritm IP certificate every six hours
[Timer]
OnCalendar=*-*-* 00,06,12,18:00:00
RandomizedDelaySec=300
Persistent=true
[Install]
WantedBy=timers.target
EOF
nginx -t
systemctl daemon-reload
systemctl enable --now avtoritm avtoritm-cert-renew.timer
systemctl restart avtoritm
systemctl reload nginx
curl --retry 8 --retry-delay 2 --retry-connrefused --fail --silent --show-error --resolve "$SITE_IP:443:127.0.0.1" "https://$SITE_IP/" -o /dev/null
echo "DEPLOYMENT_OK https://$SITE_IP/"
