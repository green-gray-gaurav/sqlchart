
INSERT INTO FCP_ITEM_DETAILS (fcp_glusr_usr_id, item_name, cat_name, cat_url, item_img, item_id, fcp_pc_item_modifieddate, item_img_500x500)

with AFD as
(
	SELECT Fk_GLUSR_USR_ID, FREE_SHOWROOM_URL, DIR_SEARCH_CAT_PRODSERV, A.IS_OLD_CATALOG OLD_CATALOG
	FROM ACTIVE_FCP_DETAILS_UPDATE 
),
pc_clnt_pcat_data_cnt as (
	SELECT PC.pc_clnt_pcat_glusr_id,
	PC.PC_CLNT_PCAT_ID,
	PCI.PC_ITEM_ID,
	PCI.PC_ITEM_NAME,
	PC.PC_CLNT_PCAT_NAME,
	PC.PC_CLNT_FLNAME,PC_ITEM_IMG_SMALL_ISDEFAULT,PC_ITEM_DESC_SMALL,PC_ITEM_IMG_SMALL,PC_CLNT_GENERATED_FLNAME,PC_CLNT_TOPLEVEL,
	REPLACE(PCI.PC_ITEM_IMG_SMALL, 'add-image.gif', 'coming-soon.gif') AS item_simg,
	REPLACE(COALESCE(PCI.PC_ITEM_IMG_LARGE, PCI.PC_IMG_SMALL_600X600), 'add-image.gif', 'coming-soon.gif') AS item_simg_LARGE,
	FROM
	PC_CLNT_PCAT PC
	JOIN PC_ITEM_TO_PC_CLNT_PCAT PCI2PC ON PCI2PC.FK_PC_CLNT_PCAT_ID = PC.PC_CLNT_PCAT_ID
	JOIN PC_ITEM PCI ON PCI.PC_ITEM_ID = PCI2PC.FK_PC_ITEM_ID
	WHERE
	PC.PC_CLNT_TOPLEVEL = 'L'
	AND LOWER(PC.PC_CLNT_PCAT_NAME) != 'other products'
	AND LOWER(PC.PC_CLNT_PCAT_NAME) != 'other product'
	AND PCI.PC_ITEM_STATUS_APPROVAL >= 10
	AND PCI.PC_ITEM_STATUS != 'x'
),
pc_clnt_pcat_data_cnt as 
(
	select pc_clnt_pcat_glusr_id as glid ,PC_CLNT_PCAT_ID as clnt_pcat_id ,
	COUNT(CASE WHEN (PCI.PC_ITEM_IMG_SMALL_ISDEFAULT = 1 or PCI.PC_ITEM_DESC_SMALL != PCI.PC_ITEM_NAME) THEN 1 END)  OVER (PARTITION BY pc_clnt_pcat_glusr_id,PC_CLNT_PCAT_ID) CNT,
	COUNT(1) OVER(PARTITION BY pc_clnt_pcat_glusr_id,PC_CLNT_PCAT_ID) CNTPCID
	from pc_clnt_pcat_data_cnt
	join PC_CLNT_PCAT_TO_PCAT on PC_CLNT_PCAT_ID = FK_PC_CLNT_PCAT_ID
	where PC_CLNT_TOPLEVEL = 'L'
)


	SELECT Fk_GLUSR_USR_ID,PC_ITEM_NAME,
	(CASE WHEN PC_CLNT_FLNAME IS NOT NULL THEN PC_CLNT_PCAT_NAME END) PC_CLNT_PCAT_NAME,
	COALESCE(FREE_SHOWROOM_URL,'') || COALESCE(PC_CLNT_FLNAME,'') MY_CAT_URL,
	ITEM_SIMG,
	PC_ITEM_ID,
	now(),
	(CASE WHEN item_simg_LARGE IS NOT NULL AND POSITION('coming-soon.gif' IN A.item_simg_LARGE)<=0 THEN item_simg_LARGE END) item_simg_LARGE,
	FROM 
	(
		SELECT Fk_GLUSR_USR_ID, item_simg, item_simg_LARGE,PC_ITEM_NAME,PC_ITEM_ID,PC_CLNT_PCAT_NAME,CNT, FREE_SHOWROOM_URL
		(CASE  	WHEN COALESCE(PC_CLNT_FLNAME,PC_CLNT_GENERATED_FLNAME)='new-item.html' THEN 'new-items.html'
				ELSE COALESCE(COALESCE(PC_CLNT_FLNAME,PC_CLNT_GENERATED_FLNAME),'new-items.html') 
		END) PC_CLNT_FLNAME, 
		FROM pc_clnt_pcat_data 
		join AFD on Fk_GLUSR_USR_ID=pc_clnt_pcat_glusr_id 
		join pc_clnt_pcat_data_cnt on PC_CLNT_PCAT_ID =clnt_pcat_id
		WHERE  PC_CLNT_TOPLEVEL = 'L' and  OLD_CATALOG=-1
	)A
	WHERE CNT>=1 and POSITION('coming-soon.gif' IN item_simg)<=0

	UNION ALL

	SELECT Fk_GLUSR_USR_ID,PC_ITEM_NAME,
	(CASE WHEN PC_CLNT_FLNAME IS NOT NULL THEN PC_CLNT_PCAT_NAME END) PC_CLNT_PCAT_NAME,
	COALESCE(FREE_SHOWROOM_URL,'') || COALESCE(PC_CLNT_FLNAME,'') MY_CAT_URL,
	item_simg,
	PC_ITEM_ID,
	now(),
	(CASE WHEN item_simg_LARGE IS NOT NULL AND POSITION('coming-soon.gif' IN A.item_simg_LARGE)<=0 THEN item_simg_LARGE END) item_simg_LARGE,
	FROM
	(
		SELECT Fk_GLUSR_USR_ID,item_simg,
		REPLACE(COALESCE(PCI.PC_ITEM_IMG_LARGE,PCI.PC_IMG_SMALL_600X600), 'add-image.gif','coming-soon.gif') item_simg_LARGE,
		PC_ITEM_NAME,PC_ITEM_ID,PC_CLNT_PCAT_NAME,PC_CLNT_FLNAME,FREE_SHOWROOM_URL, CNTPCID
		FROM pc_clnt_pcat_data 
		join AFD on Fk_GLUSR_USR_ID=pc_clnt_pcat_glusr_id 
		join pc_clnt_pcat_data_cnt on PC_CLNT_PCAT_ID =clnt_pcat_id
		WHERE PC_CLNT_TOPLEVEL = 'L' and  OLD_CATALOG<>-1
	)A
	WHERE POSITION('coming-soon.gif' IN item_simg)<=0




	UNION ALL





	SELECT A.Fk_GLUSR_USR_ID ,A.PC_ITEM_NAME AS item_name,
    CASE	WHEN CNTPCID > 0 THEN	CASE WHEN A.DIR_SEARCH_CAT_PRODSERV = 'S' THEN 'Other Services' ELSE 'Other Products' END
			ELSE 	CASE WHEN A.DIR_SEARCH_CAT_PRODSERV = 'S' THEN 'Services' ELSE 'Products' END
    END AS cat_name,
    CASE	WHEN 	( CNTPCID > 0 AND A.photo_desc_pdt_cnt = 0 AND A.name_only_pdt_cnt <= 5 ) OR 
					( CNTPCID = 0 AND A.photo_desc_pdt_cnt = 0) 
			THEN A.FREE_SHOWROOM_URL
			ELSE 	A.FREE_SHOWROOM_URL ||  CASE 	WHEN CNTPCID > 0 THEN
															CASE
																WHEN A.DIR_SEARCH_CAT_PRODSERV = 'S'
																	THEN 'other-services.html'
																ELSE 'other-products.html'
															END
													ELSE
															CASE
																WHEN A.DIR_SEARCH_CAT_PRODSERV = 'S'
																	THEN 'services.html'
																ELSE 'products.html'
															END
											END
    END AS cat_url,
    A.item_simg AS item_img,
    A.PC_ITEM_ID AS item_id,
    NOW() AS fcp_pc_item_modifieddate,
    A.ITEM_SIMG_LARGE AS item_img_500x500
	FROM
	(	SELECT Fk_GLUSR_USR_ID,PC_CLNT_PCAT_ID,PC_ITEM_NAME,item_simg,
		CASE WHEN item_simg_LARGE IS NOT NULL AND POSITION('coming-soon.gif' IN item_simg_LARGE) <= 0 THEN item_simg_LARGE END AS ITEM_SIMG_LARGE,
		PC_ITEM_ID, photo_desc_pdt_cnt, name_only_pdt_cnt, DIR_SEARCH_CAT_PRODSERV, FREE_SHOWROOM_URL
		FROM
		(	SELECT Fk_GLUSR_USR_ID,PC_CLNT_PCAT_ID,PC_ITEM_NAME,
			REPLACE(PC_ITEM_IMG_SMALL,'add-image.gif','coming-soon.gif') item_simg,
			REPLACE( COALESCE(PC_ITEM_IMG_LARGE,PC_IMG_SMALL_600X600),'add-image.gif','coming-soon.gif') item_simg_LARGE,
			PC_ITEM_ID, ROW_NUMBER() OVER (PARTITION BY Fk_GLUSR_USR_ID,PC_ITEM_ID ORDER BY PC_ITEM_ID) MYRANK1,
			COUNT(	CASE	WHEN PC_ITEM_IMG_SMALL_ISDEFAULT = 1
								OR ( PC_ITEM_DESC_SMALL IS NOT NULL AND LOWER(PC_ITEM_DESC_SMALL) != LOWER(PC_ITEM_NAME))
							THEN 1 END 
				) OVER (PARTITION BY Fk_GLUSR_USR_ID,PC_CLNT_PCAT_ID) photo_desc_pdt_cnt,
			COUNT(	CASE	WHEN (PC_ITEM_IMG_SMALL IS NULL OR PC_ITEM_IMG_SMALL_ISDEFAULT = 0)
							AND (PC_ITEM_DESC_SMALL IS NULL OR LOWER(PC_ITEM_DESC_SMALL) = LOWER(PC_ITEM_NAME))
							THEN 1 END
				) OVER (PARTITION BY Fk_GLUSR_USR_ID,PC_CLNT_PCAT_ID) name_only_pdt_cnt,
			DIR_SEARCH_CAT_PRODSERV, FREE_SHOWROOM_URL,CNTPCID
			FROM pc_clnt_pcat_data 
			join AFD on Fk_GLUSR_USR_ID=pc_clnt_pcat_glusr_id 
			left join pc_clnt_pcat_data_cnt a on PC_CLNT_PCAT_ID =a.clnt_pcat_id
			left join pc_clnt_pcat_data_cnt b on glid =Fk_GLUSR_USR_ID
			WHERE PC_CLNT_PCAT_ID IS NULL
		) X
		WHERE MYRANK1 = 1 AND POSITION('coming-soon.gif' IN item_simg) <= 0
	) A;