from app import models
from app.db import SessionLocal, init_db


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.query(models.Banner).count() == 0:
            db.add(
                models.Banner(
                    title="AI 智慧教育服务品牌",
                    image_url="/static/logo.png",
                    link_type="appointment",
                    link_value="/pages/appointment/index",
                    sort_order=1,
                    status="published",
                )
            )

        if db.query(models.Campus).count() == 0:
            db.add(
                models.Campus(
                    name="灵智启程智习室",
                    cover_url="/static/logo.png",
                    address="请在后台填写校区详细地址",
                    phone="请在后台填写联系电话",
                    business_hours="周一至周日 09:00-21:00",
                    intro="AI 学习助手与本地陪伴服务结合，提供自习、体验和学习咨询服务。",
                    status="published",
                )
            )

        if db.query(models.Course).count() == 0:
            db.add_all(
                [
                    models.Course(
                        title="AI 智习室体验课",
                        category="智习室",
                        cover_url="/static/logo.png",
                        summary="AI 学习助手 + 自主学习空间 + 本地陪伴服务。",
                        suitable_grade="小学/初中",
                        service_period="60-90 分钟",
                        price_text="预约体验",
                        tags=["AI 督学", "本地陪伴"],
                        content="到店体验智习室环境，了解学习机和学习服务方案。",
                        sort_order=1,
                        status="published",
                    ),
                    models.Course(
                        title="课后晚托服务",
                        category="晚托",
                        summary="作业管理、阅读陪伴、学习习惯培养。",
                        suitable_grade="小学",
                        price_text="到店咨询",
                        tags=["晚托", "习惯培养"],
                        sort_order=2,
                        status="published",
                    ),
                ]
            )

        if db.query(models.Article).count() == 0:
            db.add_all(
                [
                    models.Article(
                        type="material",
                        title="小学阶段学习习惯培养建议",
                        cover_url="/static/logo.png",
                        summary="帮助家长了解孩子学习习惯培养的关键点。",
                        content="稳定的学习时间、清晰的任务拆分和及时反馈，是小学阶段学习习惯培养的基础。",
                        sort_order=1,
                        status="published",
                    ),
                    models.Article(
                        type="news",
                        title="灵智启程智习室服务介绍",
                        cover_url="/static/logo.png",
                        summary="了解智习室、学习机和预约体验服务。",
                        content="灵智启程围绕智习室、智能学习机和本地陪伴服务，为家庭提供学习咨询和体验服务。",
                        sort_order=2,
                        status="published",
                    ),
                    models.Article(
                        type="activity",
                        title="校区开放日预约",
                        cover_url="/static/logo.png",
                        summary="欢迎家长预约到店参观体验。",
                        content="校区开放日支持环境参观、服务介绍和学习方案咨询。",
                        sort_order=3,
                        status="published",
                    ),
                ]
            )

        if db.get(models.Setting, "service_phone") is None:
            db.add(models.Setting(key="service_phone", value={"text": "请在后台配置客服电话"}))

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
