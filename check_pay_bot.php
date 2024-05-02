<?
require  $_SERVER['DOCUMENT_ROOT'] . '/php/lib/autoload.php';
$db_host = "";
$db_user = "";
$db_password = "";
$db_base = '';

$procent_referrer = 10;

$conn = mysqli_connect($db_host, $db_user, $db_password, $db_base) or die(mysqli_error($conn));

use YooKassa\Client;

$client = new Client();
$client->setAuth('', '');


// Проверяем статус оплаты
$pay_status = mysqli_query($conn, "SELECT * FROM `payment` WHERE `status` = 'pending'");
$date = date('Y-m-d H:i:s');
$dateTo = date("Y-m-d H:i:s", strtotime("+1 month"));
// Получаем список платежей циклом
while ($row = mysqli_fetch_assoc($pay_status)) {
    $paymentId = $row['pay_key']; // Получаем ключ платежа
    $payment = $client->getPaymentInfo($paymentId); // Получаем информацию о платеже
    $pay_check = $payment->getstatus(); // Получаем статус оплаты

    // Если платеж прошел, то обновляем статус платежа
    if ($pay_check == 'waiting_for_capture' or $pay_check == 'succeeded') {
        // Обновляем статус платежа
        mysqli_query($conn, "UPDATE payment SET status = '" . $pay_check . "'  WHERE pay_key = '" . $paymentId . "'");
        $query = mysqli_query($conn, "SELECT * FROM users WHERE user_id = '" . $row['user_id'] . "'");
        $all_info = mysqli_fetch_assoc($query);
        $balance = $all_info['balance'];
        mysqli_query($conn, "SET NAMES 'utf8");
        mysqli_query($conn, "SET CHARACTER SET 'utf8'");
        $type = explode('_', $row['pay_type']);
        if ($type[0] == 'subscribe') {
            if ($type[1] == '10') {
                $date_to = date("Y-m-d H:i:s", strtotime("+10 minutes"));
                $period = $type[1] . ' минут';
            } else if ($type[1] == '1') {
                $date_to = date("Y-m-d H:i:s", strtotime("+1 days"));
                $period = $type[1] . ' день';
            } else if ($type[1] == '7') {
                $date_to = date("Y-m-d H:i:s", strtotime("+7 days"));
                $period = $type[1] . ' дней';
            } else if ($type[1] == '30') {
                $date_to = date("Y-m-d H:i:s", strtotime("+30 days"));
                $period = $type[1] . ' дней';
            } else if ($type[1] == '180') {
                $date_to = date("Y-m-d H:i:s", strtotime("+180 days"));
                $period = $type[1] . ' дней';
            } else if ($type[1] == '360') {
                $date_to = date("Y-m-d H:i:s", strtotime("+360 days"));
                $period = $type[1] . ' дней';
            } else {
                $date_to = date("Y-m-d H:i:s", strtotime("+10 minutes"));
                $period = $type[1] . ' минут';
            }
            if ($balance != 0) {
                $sum = $balance - $row['sum'];
                mysqli_query($conn, "UPDATE users SET balance='" . $sum . "' WHERE user_id='" . $row['user_id'] . "'");
            }
            mysqli_query($conn, "UPDATE users SET user_subcribe_end='" . $date_to . "' WHERE user_id='" . $row['user_id'] . "'");
            mysqli_query($conn, "INSERT INTO subscribe SET user_id='" . $row['user_id'] . "', date_from='" . $date . "', date_to='" . $date_to . "', period='" . $period . "', status=true");
            mysqli_query($conn, "INSERT INTO operations SET user_id='" . $row['user_id'] . "', transaction_type='subscribe', transaction='Оформление подписки. Период действия  " . $period . ". ID операции: " . $paymentId . "'");

            $msg = "✅ <b>Оформление подписки</b>";
            $msg .= " \n ";
            $msg .= "<b>├ ID операции:</b> <code>$paymentId</code>";
            $msg .= " \n ";
            $msg .= '<b>└  Период действия:</b> <code>' . $period . '</code>';
            $msg = urlencode($msg);

            $msg_owner = "✅ <b>Оформление подписки</b>";
            $msg_owner .= " \n ";
            $msg_owner .= "<b>Сумма: </b> <code>" . $row['sum'] . "</code>";
            $msg_owner = urlencode($msg_owner);
            file_get_contents('https://api.telegram.org/<token>/sendMessage?chat_id=' . $row['user_id'] . '&text=' . $msg . '&parse_mode=HTML');
        } else {
            $sum = $balance + $row['sum'];
            $invitated = $all_info['invitated'];
            if ($invitated) {
                $query = mysqli_query($conn, "SELECT * FROM users WHERE user_id = '" . $invitated . "'");
                $invited_user = mysqli_fetch_assoc($query);
                $procent_inv = (int)$row['sum'] * ($procent_referrer / 100);
                if ($procent_inv <= 1) {
                    $procent_inv = 1;
                }
                $summ_inv = (int)$invited_user['balance'] + $procent_inv;
                mysqli_query($conn, "UPDATE users SET balance='" . $summ_inv . "' WHERE user_id='" . $invitated . "'");
                $invitated_user_name = $invited_user['user_name'];
                $msg = "✅ <b>Зачисление средств</b>";
                $msg .= " \n ";
                $msg .= "<b>├ Приглашенный пользователь:</b> @$invitated_user_name";
                $msg .= " \n ";
                $msg .= '<b>├ Сумма зачисления:</b> <code>' . $procent_inv . '₽</code>';
                $msg .= " \n ";
                $msg .= '<b>└ Баланс:</b> <code>' . $summ_inv . '₽</code>';
                $msg = urlencode($msg);
                file_get_contents('https://api.telegram.org/<token>/sendMessage?chat_id=' . $invitated . '&text=' . $msg . '&parse_mode=HTML');
            }
            mysqli_query($conn, "UPDATE users SET balance='" . $sum . "' WHERE user_id='" . $row['user_id'] . "'");
            mysqli_query($conn, "INSERT INTO operations SET user_id='" . $row['user_id'] . "', transaction_type='replenishment', transaction='+" . $row['sum'] . "₽ - Пополнение баланса. Заказ: " . $paymentId . "'");
            $sum_add = $row['sum'];
            $msg = "✅ <b>Зачисление средств</b>";
            $msg .= " \n ";
            $msg .= "<b>├ ID операции:</b> <code>$paymentId</code>";
            $msg .= " \n ";
            $msg .= '<b>├ Сумма зачисления:</b> <code>' . $sum_add . '₽</code>';
            $msg .= " \n ";
            $msg .= '<b>└ Баланс:</b> <code>' . $sum . '₽</code>';
            $msg = urlencode($msg);

            $msg_owner = "✅ <b>Зачисление средств</b>";
            $msg_owner .= " \n ";
            $msg_owner .= "<b>Сумма: </b> <code>" . $sum_add . "₽</code>";
            $msg_owner = urlencode($msg_owner);
            file_get_contents('https://api.telegram.org/<token>/sendMessage?chat_id=' . $row['user_id'] . '&text=' . $msg . '&parse_mode=HTML');
        }
    }
}

$subscribe = mysqli_query($conn, "SELECT * FROM `subscribe` WHERE `status` = true");
while ($row = mysqli_fetch_assoc($subscribe)) {
    $date_exp = strtotime($row['date_to']);
    if ($date_exp <= strtotime($date)) {
        mysqli_query($conn, "UPDATE subscribe SET status = false  WHERE id = '" . $row['id'] . "'");
        mysqli_query($conn, "UPDATE users SET user_subcribe_end = null  WHERE user_id = '" . $row['user_id'] . "'");
    }
}
