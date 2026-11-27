<?php

declare(strict_types=1);

namespace App\Core;

use PDO;
use PDOException;
use PDOStatement;
use RuntimeException;
use Throwable;

/**
 * Conexión PDO única por proceso (singleton perezoso) para MariaDB 10.5.
 *
 * - Prepared statements reales (EMULATE_PREPARES = false) => sin inyección SQL.
 * - Sesión en UTC y utf8mb4 (emojis de WhatsApp/IG).
 * - Reconexión automática para procesos CLI largos (cron_worker) si el servidor
 *   cerró la conexión por wait_timeout ("MySQL server has gone away").
 */
final class Database
{
    private static ?PDO $pdo = null;

    public static function connection(): PDO
    {
        if (self::$pdo === null) {
            self::$pdo = self::connect();
        }
        return self::$pdo;
    }

    private static function connect(): PDO
    {
        $cfg = Config::get('database');
        $dsn = sprintf(
            'mysql:host=%s;port=%d;dbname=%s;charset=%s',
            $cfg['host'],
            (int) $cfg['port'],
            $cfg['database'],
            $cfg['charset']
        );

        try {
            $pdo = new PDO($dsn, $cfg['username'], $cfg['password'], [
                PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES   => false,
                PDO::ATTR_STRINGIFY_FETCHES  => false,
                PDO::ATTR_PERSISTENT         => false, // en hosting compartido evita agotar conexiones
                PDO::ATTR_TIMEOUT            => 5,
                PDO::MYSQL_ATTR_INIT_COMMAND => sprintf(
                    "SET NAMES %s COLLATE %s, time_zone = '+00:00', sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'",
                    $cfg['charset'],
                    $cfg['collation']
                ),
            ]);
        } catch (PDOException $e) {
            // No filtrar credenciales en el mensaje
            throw new RuntimeException('No se pudo conectar a la base de datos: ' . $e->getCode(), 0, $e);
        }

        return $pdo;
    }

    /** Ejecuta una consulta parametrizada con reintento único ante desconexión. */
    public static function query(string $sql, array $params = []): PDOStatement
    {
        try {
            return self::run($sql, $params);
        } catch (PDOException $e) {
            if (self::isConnectionLost($e) && !self::connection()->inTransaction()) {
                self::$pdo = null;
                return self::run($sql, $params);
            }
            throw $e;
        }
    }

    private static function run(string $sql, array $params): PDOStatement
    {
        $stmt = self::connection()->prepare($sql);
        foreach ($params as $key => $value) {
            $param = is_int($key) ? $key + 1 : (str_starts_with($key, ':') ? $key : ':' . $key);
            $type = match (true) {
                is_int($value)  => PDO::PARAM_INT,
                is_bool($value) => PDO::PARAM_BOOL,
                $value === null => PDO::PARAM_NULL,
                default         => PDO::PARAM_STR,
            };
            $stmt->bindValue($param, $value, $type);
        }
        $stmt->execute();
        return $stmt;
    }

    /** @return array<string, mixed>|null */
    public static function fetch(string $sql, array $params = []): ?array
    {
        $row = self::query($sql, $params)->fetch();
        return $row === false ? null : $row;
    }

    /** @return list<array<string, mixed>> */
    public static function fetchAll(string $sql, array $params = []): array
    {
        return self::query($sql, $params)->fetchAll();
    }

    public static function fetchValue(string $sql, array $params = []): mixed
    {
        $value = self::query($sql, $params)->fetchColumn();
        return $value === false ? null : $value;
    }

    /** INSERT simple a partir de un array asociativo. Devuelve el ID insertado. */
    public static function insert(string $table, array $data): int
    {
        self::assertIdentifier($table);
        $columns = array_keys($data);
        array_walk($columns, [self::class, 'assertIdentifier']);

        $sql = sprintf(
            'INSERT INTO `%s` (`%s`) VALUES (%s)',
            $table,
            implode('`, `', $columns),
            implode(', ', array_map(static fn ($c) => ':' . $c, $columns))
        );
        self::query($sql, self::normalize($data));
        return (int) self::connection()->lastInsertId();
    }

    /** UPDATE con WHERE parametrizado. Devuelve filas afectadas. */
    public static function update(string $table, array $data, string $where, array $whereParams = []): int
    {
        self::assertIdentifier($table);
        $sets = [];
        $params = [];
        foreach ($data as $column => $value) {
            self::assertIdentifier($column);
            $sets[] = "`{$column}` = :set_{$column}";
            $params['set_' . $column] = $value;
        }
        $sql = sprintf('UPDATE `%s` SET %s WHERE %s', $table, implode(', ', $sets), $where);
        return self::query($sql, self::normalize($params) + $whereParams)->rowCount();
    }

    /**
     * Ejecuta un callback dentro de una transacción.
     * @template T
     * @param callable(PDO): T $callback
     * @return T
     */
    public static function transaction(callable $callback): mixed
    {
        $pdo = self::connection();
        $pdo->beginTransaction();
        try {
            $result = $callback($pdo);
            $pdo->commit();
            return $result;
        } catch (Throwable $e) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            throw $e;
        }
    }

    public static function disconnect(): void
    {
        self::$pdo = null;
    }

    /** Arrays => JSON; bool => int. */
    private static function normalize(array $data): array
    {
        foreach ($data as $k => $v) {
            if (is_array($v)) {
                $data[$k] = json_encode($v, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR);
            } elseif (is_bool($v)) {
                $data[$k] = (int) $v;
            }
        }
        return $data;
    }

    private static function assertIdentifier(string $name): void
    {
        if (!preg_match('/^[a-zA-Z_][a-zA-Z0-9_]{0,63}$/', $name)) {
            throw new RuntimeException("Identificador SQL inválido: {$name}");
        }
    }

    private static function isConnectionLost(PDOException $e): bool
    {
        $code = (int) ($e->errorInfo[1] ?? 0);
        return in_array($code, [2006, 2013], true)  // gone away / lost connection
            || str_contains($e->getMessage(), 'gone away');
    }
}
