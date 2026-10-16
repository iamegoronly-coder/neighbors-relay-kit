# Caddy с постквантовым TLS

[English](caddy.md) · [Русский](caddy.ru.md) · [Deutsch](caddy.de.md)

Caddy 2.10 и новее (сборка Go 1.24+) по умолчанию предлагает гибридный обмен ключами TLS 1.3 `X25519MLKEM768` наряду с классическим X25519. Пакет `caddy` из Ubuntu 24.04 имеет версию 2.6.2 и этого не поддерживает, поэтому комплект использует официальный репозиторий Caddy на Cloudsmith.

Не добавляйте директиву `curves`: настройки по умолчанию уже предпочитают гибрид, а явным списком легко исключить необходимые старым клиентам группы.

<a id="new-server"></a>
## Новый сервер

Выполняйте из корня проверенного репозитория. В `scripts/verify-caddy-key.py` закреплён полный отпечаток основного ключа:
`65760C51EDEA2017CEA2CA15155B6D79CA56EA34`.
Он сверен с [официальными метаданными репозитория Caddy](https://cloudsmith.io/~caddy/repos/stable/packages/). Другой, просроченный, отозванный, повреждённый или дополнительный основной ключ останавливает установку до добавления доверия. При ротации независимо проверьте новый ключ и обновление комплекта; не обходите проверку и не берите ожидаемый отпечаток из того же скачанного файла.

```sh
(
  set -eu
  apt-get install -y python3 debian-keyring debian-archive-keyring apt-transport-https curl gnupg
  KEY_WORK=$(mktemp -d)
  trap 'rm -rf "$KEY_WORK"' EXIT HUP INT TERM
  curl --proto '=https' --proto-redir '=https' --tlsv1.2 -fLsS --max-time 60 \
    'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' -o "$KEY_WORK/caddy.key"
  python3 scripts/verify-caddy-key.py "$KEY_WORK/caddy.key"
  gpg --batch --yes --dearmor --output "$KEY_WORK/caddy.gpg" "$KEY_WORK/caddy.key"
  install -m 644 "$KEY_WORK/caddy.gpg" /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  printf '%s\n' 'deb [signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg] https://dl.cloudsmith.io/public/caddy/stable/deb/debian any-version main' \
    > /etc/apt/sources.list.d/caddy-stable.list
  chmod 644 /etc/apt/sources.list.d/caddy-stable.list
  apt-get update
  apt-cache policy caddy
)
```

`Candidate` должен происходить с `dl.cloudsmith.io` и иметь версию не ниже 2.10. Установите именно эту версию и закрепите её для плановых обновлений:

```sh
V=2.11.7                      # replace with the exact Candidate version if it is newer
apt-get install -y "caddy=$V"
apt-mark hold caddy
caddy version
sh bin/require-pq-caddy       # from this kit
```

Затем настройте сайт по `config/Caddyfile.example` (README, шаг 4).

<a id="upgrading"></a>
## Обновление

Для сервера, где перед реле уже работает старый Caddy. Занимает 15–20 минут. При перезапуске Caddy открытые WebSocket-соединения кратко прерываются; клиенты подключатся снова, сохранённые события не затрагиваются (strfry продолжает работать). Несколько реле обновляйте по одному.

Переменные shell действуют лишь в текущем SSH-сеансе; после переподключения задайте заново. Каждый блок запускайте только после успешного предыдущего. При ошибке остановитесь, не переходите к перезапуску.

### 1. Резервная копия на сервере

```sh
BK=/root/caddy-before-upgrade-$(date -u +%Y%m%dT%H%M%SZ); mkdir -m 700 "$BK"
caddy version | tee "$BK/version.txt"; dpkg -l caddy | tail -1 | tee -a "$BK/version.txt"
cp -a "$(command -v caddy)" "$BK/caddy"
cp -a /etc/caddy "$BK/etc-caddy"
OLD_VERSION=$(dpkg-query -W -f='${Version}' caddy)
printf '%s\n' "$OLD_VERSION" > "$BK/package-version"
mkdir -m 700 "$BK/package"
(
    set -eu
    cd "$BK/package"
    apt-get download "caddy=$OLD_VERSION"
    set -- ./caddy_*.deb
    [ "$#" -eq 1 ] && [ -f "$1" ]
    [ "$(dpkg-deb -f "$1" Package)" = caddy ]
    [ "$(dpkg-deb -f "$1" Version)" = "$OLD_VERSION" ]
    sha256sum "$1" > SHA256SUMS
)
ls -la /var/lib/caddy/.local/share/caddy/certificates/*/ | tee "$BK/certs.txt"
/usr/local/libexec/strfry-health
```

Не обновляйте без сохранённого и проверенного `.deb` именно установленной версии. Если скачать его уже нельзя, возьмите точно этот пакет из доверенного кеша/архива и повторите проверки Package/Version/контрольной суммы; не подменяйте текущим кандидатом. Копия исполняемого файла — аварийный запас, не полноценный откат пакета.

Если Caddy обслуживает и сайт, сохраните отпечаток страницы для сравнения после обновления:
`curl -fsS https://your.domain/ | sha256sum | tee "$BK/site.sha256"`.

### 2. Подключение репозитория

Как в разделе [Новый сервер](#new-server), до `apt-cache policy caddy`, затем задайте `V` равной точной версии `Candidate` (2.10+).

### 3. Проверка текущего Caddyfile новым бинарником до установки

Установка пакета перезапускает Caddy, поэтому сначала проверьте конфигурацию распакованной копией. Сертификаты и рабочие данные не затрагиваются:

```sh
(
    set -eu
    T=$(mktemp -d)
    trap 'rm -rf "$T"' 0
    cd "$T"
    apt-get download "caddy=$V"
    dpkg-deb -x caddy_*.deb x
    ./x/usr/bin/caddy version
    XDG_DATA_HOME="$T/data" XDG_CONFIG_HOME="$T/config" \
      ./x/usr/bin/caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
)
```

Ожидается `Valid configuration`. Предупреждения вроде «input is not formatted» косметические; не запускайте `caddy fmt --overwrite`, это перепишет файл. При любой ошибке остановитесь.

### 4. Установка

`--force-confold` сохраняет ваш `/etc/caddy/Caddyfile` вместо пакетного образца.

```sh
(
    set -eu
    # Reapply this kit's hold policy on success AND if apt fails.
    trap 'apt-mark hold caddy' 0
    apt-mark unhold caddy
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
      -o Dpkg::Options::=--force-confold -o Dpkg::Options::=--force-confdef "caddy=$V"
    cmp /etc/caddy/Caddyfile "$BK/etc-caddy/Caddyfile"
    echo "Caddyfile unchanged"
    systemctl restart caddy
    sleep 3
    systemctl is-active caddy
    journalctl -u caddy --since '2 min ago' --no-pager | grep -E '"level":"(error|warn)"|obtaining' | tail -20
)
```

Неожиданный запрос сертификата для домена с действующим сертификатом требует проверки путей хранения и прав; сама строка журнала ещё не доказывает потерю хранилища.

### 5. Проверка

На сервере: `/usr/local/libexec/strfry-health`, NIP-11 через `curl`, `/metrics` → 404 и отпечаток сайта, если сохраняли. С машины с OpenSSL 3.5+:

```sh
sh scripts/check-pq-tls.sh your.domain
```

### Откат на точно сохранённый пакет

Задайте `BK` каталогом копии из шага 1. Оставьте Cloudsmith подключённым. Процедура восстанавливает сохранённую версию, а не кандидата дистрибутива, и возвращает hold даже при ошибке установки. Менеджер пакетов может перезапустить Caddy: сначала восстановите и проверьте сохранённую конфигурацию. Существующее хранилище сертификатов не заменяется.

```sh
(
    set -eu
    cd "$BK/package"
    sha256sum -c SHA256SUMS
    set -- ./caddy_*.deb
    [ "$#" -eq 1 ] && [ -f "$1" ]
    [ "$(dpkg-deb -f "$1" Package)" = caddy ]
    [ "$(dpkg-deb -f "$1" Version)" = "$(cat "$BK/package-version")" ]
    CHECK_DIR=$(mktemp -d)
    trap 'rm -rf "$CHECK_DIR"' 0
    cp -a "$BK/etc-caddy/." /etc/caddy/
    XDG_DATA_HOME="$CHECK_DIR/data" XDG_CONFIG_HOME="$CHECK_DIR/config" \
      "$BK/caddy" validate --config /etc/caddy/Caddyfile --adapter caddyfile
    trap 'apt-mark hold caddy; rm -rf "$CHECK_DIR"' 0
    apt-mark unhold caddy
    DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-downgrades \
      -o Dpkg::Options::=--force-confold -o Dpkg::Options::=--force-confdef "$PWD/${1#./}"
    [ "$(dpkg-query -W -f='${Version}' caddy)" = "$(cat "$BK/package-version")" ]
    caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
    systemctl restart caddy
    systemctl is-active caddy
)
```

После отката повторите проверки реле/сайта и внешнего TLS. Если старая версия не поддерживала гибридный TLS, ограничение вернётся; отметьте гибридную проверку как неуспешную.

### Аварийное восстановление бинарника

Если восстановить пакет невозможно, временно верните сохранённый исполняемый файл:
`systemctl stop caddy && cp -a "$BK/caddy" /usr/bin/caddy && systemctl start caddy`.
Это не восстанавливает состояние пакетного менеджера; до следующего обновления согласуйте его с сохранённым пакетом. Не подменяйте незаметно старым Caddy из Ubuntu: можно потерять постквантовый TLS. strfry, его база, таймеры и firewall в эту процедуру не входят.
