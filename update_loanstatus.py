import os
import oracledb
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def main():
    # โหลด config จาก environment variables
    user = os.getenv("ORACLE_USER")
    password = os.getenv("ORACLE_PASS")
    dsn = os.getenv("ORACLE_DSN")
    spreadsheet_name = os.getenv("SPREADSHEET_NAME")

    # เชื่อม Oracle
    db_config = {
        "user": user,
        "password": password,
        "dsn": dsn
    }

    # ตั้งค่า Instant Client สำหรับ Oracle ถ้าจำเป็น (เช็คว่าต้องใช้หรือไม่)
    # oracledb.init_oracle_client(lib_dir="/path/to/instantclient")  # ถ้ารันบน Linux VM อาจไม่ต้องใช้

    sql = """
    SELECT
        mb.card_person || '' || TO_CHAR(mb.birth_date, 'DD') || '/' || TO_CHAR(mb.birth_date, 'MM') || '/' || (TO_CHAR(mb.birth_date, 'YYYY') + 543) AS login,
        mb.card_person AS บัตรประชาชน,
        mb.member_no AS เลขสมาชิก,
        TRIM(ft_memname(mb.coop_id, mb.member_no)) AS ชื่อ,
        mb.addr_phone AS หมายเลขโทรศัพท์,
        TO_CHAR(mb.birth_date, 'dd MONTH yyyy', 'NLS_CALENDAR=''THAI BUDDHA'' NLS_DATE_LANGUAGE=THAI') AS วันเดือนปีเกิด,

        lre.reqregister_docno AS เลขที่ลงรับ,
        TO_CHAR(lre.lnreqreceive_date, 'dd MONTH yyyy', 'NLS_CALENDAR=''THAI BUDDHA'' NLS_DATE_LANGUAGE=THAI') AS วันที่ลงรับ,
        lre.remark AS หมายเหตุ,
        lre.entry_id AS ผู้ลงรับ,
        lre.reqregister_status AS สถานะลงรับ,

        req.loanrequest_docno AS เลขใบคำขอกู้,
        TO_CHAR(req.loanrequest_date, 'dd MONTH yyyy', 'NLS_CALENDAR=''THAI BUDDHA'' NLS_DATE_LANGUAGE=THAI') AS วันที่ลงใบคำขอกู้,
        req.entry_id AS ผู้ลงใบคำขอ,
        req.loanrequest_status AS สถานะใบคำขอ,

        lt.loantype_desc AS ประเภทเงินกู้,

        ln.loancontract_no AS เลขสัญญา,
        TO_CHAR(ln.loanapprove_date, 'dd MONTH yyyy', 'NLS_CALENDAR=''THAI BUDDHA'' NLS_DATE_LANGUAGE=THAI') AS วันที่อนุมัติ,
        ln.approve_id AS ผู้อนุมัติ,
        ln.loanapprove_amt AS ยอดอนุมัติ,
        TO_CHAR(ln.startcont_date, 'dd MONTH yyyy', 'NLS_CALENDAR=''THAI BUDDHA'' NLS_DATE_LANGUAGE=THAI') AS วันที่เริ่มสัญญา,

        so.payoutclr_amt AS หักอื่น,
        so.payoutnet_amt AS จ่ายจริง,
        cb.bank_desc AS ธนาคาร,
        ln.expense_accid AS เลขบัญชี,

        CASE
            WHEN so.payoutnet_amt IS NOT NULL AND so.payoutnet_amt > 0 THEN
                'จ่ายเงินกู้แล้ว วันที่ ' ||
                TO_CHAR(so.slip_date, 'dd MONTH yyyy', 'NLS_CALENDAR=''THAI BUDDHA'' NLS_DATE_LANGUAGE=THAI') ||
                ' จำนวน ' || TO_CHAR(so.payoutnet_amt, '9G999G999G990D00') || ' บาท ' ||
                cb.bank_desc || ' เลขบัญชี ' || ln.expense_accid
            WHEN ln.loancontract_no IS NOT NULL THEN
                'สัญญากู้ของท่านอนุมัติแล้ว อยู่ในขั้นตอนการจ่ายเงินกู้'
            WHEN req.loanrequest_docno IS NOT NULL THEN
                'สัญญากู้ของท่านลงบันทึกใบคำขอกู้เงินแล้ว รออนุมัติ'
            WHEN lre.reqregister_docno IS NOT NULL THEN
                'สหกรณ์ได้รับสัญญากู้ของท่านแล้ว อยู่ในขั้นตอนตรวจสอบเอกสารใบคำขอกู้'
            ELSE
                'ยังไม่มีการดำเนินการ'
        END AS สถานะกระบวนการกู้

    FROM
        mbmembmaster mb
    LEFT JOIN lnreqloanregister lre ON mb.member_no = lre.member_no
    LEFT JOIN lnreqloan req ON req.ref_registerno = lre.reqregister_docno
    LEFT JOIN lncontmaster ln ON req.loanrequest_docno = ln.loanrequest_docno
    LEFT JOIN cmucfbank cb ON ln.expense_bank = cb.bank_code
    LEFT JOIN slslippayout so ON ln.loancontract_no = so.loancontract_no
    LEFT JOIN lnloantype lt ON COALESCE(req.loantype_code, lre.loantype_code) = lt.loantype_code

    WHERE
        (lre.lnreqreceive_date > SYSDATE - 30 OR req.loanrequest_date > SYSDATE - 30)
        AND NVL(req.loanrequest_status, 0) <> -9
        AND NVL(so.slip_status, 0) <> -9
        AND NVL(req.expense_code, 'NA') <> 'CSH'

    ORDER BY
       lre.lnreqreceive_date, req.loanrequest_date
    """

    try:
        with oracledb.connect(**db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

        # เชื่อม Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open(spreadsheet_name).sheet1

        # ล้างข้อมูลเก่าใน sheet
        sheet.clear()

        # เขียน header
        sheet.append_row(columns)

        # เขียนข้อมูลทีละแถว
        for row in rows:
            sheet.append_row(row)

        print("✅ อัปเดตข้อมูล Google Sheet เรียบร้อย")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")

if __name__ == "__main__":
    main()
