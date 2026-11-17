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
                    intro="提供安静自习场地、智能设备展示和预约到店体验服务。",
                    status="published",
                )
            )

        if db.query(models.Course).count() == 0:
            db.add_all(
                [
                    models.Course(
                        title="智能设备体验活动",
                        category="智习室",
                        cover_url="/static/logo.png",
                        summary="了解智能学习设备的功能、配置与使用场景。",
                        suitable_grade="小学/初中",
                        service_period="60-90 分钟",
                        price_text="预约到店体验",
                        tags=["设备展示", "配置咨询"],
                        content="到店了解智习室环境，体验智能设备并咨询适合的配置方案。",
                        sort_order=1,
                        status="published",
                    ),
                    models.Course(
                        title="文化兴趣活动",
                        category="兴趣活动",
                        summary="通过参访、阅读分享和文化体验拓展兴趣。",
                        suitable_grade="小学",
                        price_text="到店咨询",
                        tags=["文化体验", "兴趣拓展"],
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
                        title="空间开放安排公告",
                        cover_url="/static/logo.png",
                        summary="空间公告：查看开放时间与到店须知。",
                        content="请家长提前查看空间开放时间和到店须知，如有调整将通过空间公告更新。",
                        sort_order=1,
                        status="published",
                    ),
                    models.Article(
                        type="news",
                        title="灵智启程智习室服务介绍",
                        cover_url="/static/logo.png",
                        summary="了解智习室、智能设备和预约到店体验服务。",
                        content="灵智启程提供自习场地、智能设备展示、配置咨询和到店体验服务。",
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
        if db.get(models.Setting, "learning_machine_posters") is None:
            db.add(models.Setting(key="learning_machine_posters", value={"posters": []}))

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
